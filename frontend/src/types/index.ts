/**
 * ContextAI Type Definitions
 */

export type IntelligenceMode = 'swift' | 'balanced' | 'deep';
export type ThemeMode = 'dark' | 'light' | 'system';

export interface UserPreferences {
  theme: ThemeMode;
  defaultMode: IntelligenceMode;
  enterToSend: boolean;
  developerModeEnabled: boolean;
}

export interface ModeOption {
  id: IntelligenceMode;
  name: string;
  description: string;
  subtext: string;
}

export interface Message {
  id?: string;
  role: 'user' | 'assistant';
  content: string;
  created_at?: string;
  context_summary?: string | null;
  messages_in_context?: number;
  mode?: IntelligenceMode;
  model_label?: string;
}

export interface Conversation {
  id: string;
  title: string;
  created_at?: string;
  updated_at?: string;
  mode?: IntelligenceMode;
  messages_in_context?: number;
  context_summary?: string | null;
  messages_count?: number;
  messages?: Message[];
}

export interface ChatRequest {
  conversation_id: string;
  message: string;
  mode: IntelligenceMode;
}

export interface ChatResponse {
  conversation_id: string;
  reply: string;
  mode?: IntelligenceMode;
  model_label?: string;
  context_summary?: string | null;
  messages_in_context?: number;
}

export interface HealthCheckResponse {
  status: string;
  version?: string;
  database?: string;
  llm_configured?: boolean;
  supported_modes?: string[];
  [key: string]: unknown;
}

export interface BackendStatus {
  isChecking: boolean;
  isAvailable: boolean;
  lastChecked: Date | null;
  error?: string | null;
  endpointUrl: string;
}
