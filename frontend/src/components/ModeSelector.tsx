import React, { useState, useRef, useEffect } from 'react';
import { Zap, SlidersHorizontal, Brain, ChevronDown, Check } from 'lucide-react';
import { IntelligenceMode } from '../types';

interface ModeSelectorProps {
  mode: IntelligenceMode;
  onModeChange: (newMode: IntelligenceMode) => void;
  disabled?: boolean;
}

interface ModeConfig {
  id: IntelligenceMode;
  name: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
}

const MODES: ModeConfig[] = [
  {
    id: 'swift',
    name: 'Swift',
    description: 'Fast responses',
    icon: Zap,
  },
  {
    id: 'balanced',
    name: 'Balanced',
    description: 'Everyday intelligence',
    icon: SlidersHorizontal,
  },
  {
    id: 'deep',
    name: 'Deep',
    description: 'Advanced reasoning',
    icon: Brain,
  },
];

export const ModeSelector: React.FC<ModeSelectorProps> = ({
  mode,
  onModeChange,
  disabled = false,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const currentConfig = MODES.find((m) => m.id === mode) || MODES[1];
  const CurrentIcon = currentConfig.icon;

  // Handle click outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  // Handle escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  const handleSelect = (selectedMode: IntelligenceMode) => {
    onModeChange(selectedMode);
    setIsOpen(false);
  };

  return (
    <div className="relative inline-block text-left" ref={containerRef}>
      {/* Trigger button directly in or above composer */}
      <button
        type="button"
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
        aria-haspopup="true"
        aria-expanded={isOpen}
        aria-label={`Select intelligence mode. Currently: ${currentConfig.name}`}
        className={`flex items-center gap-1.5 px-2.5 py-1 text-xs rounded-lg transition-colors border cursor-pointer ${
          disabled
            ? 'opacity-50 cursor-not-allowed bg-app-surface border-app-subtle text-app-muted'
            : isOpen
            ? 'bg-app-composer text-app-primary border-app-hover'
            : 'bg-app-surface hover:bg-app-composer text-app-secondary hover:text-app-primary border-app-subtle'
        }`}
      >
        <CurrentIcon className="w-3.5 h-3.5 text-app-primary" />
        <span className="font-medium text-app-primary">{currentConfig.name}</span>
        <ChevronDown
          className={`w-3 h-3 text-app-muted transition-transform duration-150 ${
            isOpen ? 'rotate-180' : ''
          }`}
        />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div
          role="menu"
          className="absolute bottom-full left-0 mb-2 w-72 bg-app-sidebar border border-app-subtle rounded-xl shadow-xl p-1.5 z-50 animate-in fade-in zoom-in-95 duration-150 focus:outline-none"
        >
          <div className="px-2.5 py-1.5 text-[10px] font-semibold text-app-muted uppercase tracking-wider border-b border-app-subtle mb-1">
            Intelligence Mode
          </div>

          <div className="space-y-0.5">
            {MODES.map((item) => {
              const isSelected = item.id === mode;
              const ItemIcon = item.icon;

              return (
                <button
                  key={item.id}
                  role="menuitem"
                  type="button"
                  onClick={() => handleSelect(item.id)}
                  className={`w-full flex items-center justify-between px-2.5 py-2 rounded-lg text-left transition-colors text-xs cursor-pointer ${
                    isSelected
                      ? 'bg-app-surface text-app-primary font-medium border border-app-subtle'
                      : 'text-app-secondary hover:bg-app-main hover:text-app-primary border border-transparent'
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div
                      className={`w-6 h-6 rounded-md flex items-center justify-center shrink-0 border ${
                        isSelected
                          ? 'bg-app-composer border-app-subtle text-app-primary'
                          : 'bg-app-surface border-app-subtle text-app-muted'
                      }`}
                    >
                      <ItemIcon className="w-3.5 h-3.5" />
                    </div>
                    <div className="min-w-0">
                      <div className="text-app-primary text-xs font-medium leading-none mb-1">
                        {item.name}
                      </div>
                      <div className="text-[11px] text-app-muted truncate">
                        {item.description}
                      </div>
                    </div>
                  </div>

                  {isSelected && (
                    <Check className="w-3.5 h-3.5 text-app-primary shrink-0 ml-2" />
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
