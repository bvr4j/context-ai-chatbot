/**
 * Centralized API service for ContextAI backend communication.
 * Communicates with the FastAPI backend (SQLite + LLM).
 */

import { Conversation, Message, ChatResponse, HealthCheckResponse, IntelligenceMode } from '../types';

const STORAGE_KEY = 'contextai_api_base_url';

export const getDefaultApiBaseUrl = (): string => {
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (envUrl && typeof envUrl === 'string' && envUrl.trim().length > 0) {
    return envUrl.trim().replace(/\/+$/, '');
  }
  // When deployed on Vercel (unified domain without separate port 3000/5173),
  // default to relative path "" so /api and /health route to backend via vercel.json rewrites.
  if (typeof window !== 'undefined' && window.location.origin) {
    const isStandaloneDev = window.location.port === '3000' || window.location.port === '5173';
    if (!isStandaloneDev) {
      return '';
    }
  }
  return 'http://localhost:8000';
};

export const getApiBaseUrl = (): string => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored && stored.trim().length > 0) {
      return stored.trim().replace(/\/+$/, '');
    }
  } catch {
    // localStorage may be unavailable in restricted environments
  }
  return getDefaultApiBaseUrl();
};

export const setApiBaseUrl = (url: string): string => {
  const sanitized = url.trim().replace(/\/+$/, '');
  try {
    localStorage.setItem(STORAGE_KEY, sanitized);
  } catch (err) {
    console.error('Failed to save API base URL to localStorage', err);
  }
  return sanitized;
};

export const resetApiBaseUrl = (): string => {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (err) {
    console.error('Failed to reset API base URL in localStorage', err);
  }
  return getDefaultApiBaseUrl();
};

export class ApiError extends Error {
  status?: number;
  isNetworkError: boolean;

  constructor(message: string, status?: number, isNetworkError: boolean = false) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.isNetworkError = isNetworkError;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const url = `${baseUrl}${normalizedPath}`;

  const headers: Record<string, string> = {
    'Accept': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  if (options.body && typeof options.body === 'string' && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 50000); // 50s timeout for LLM responses

  try {
    const response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      let errorMessage = `Request failed with status ${response.status}`;
      try {
        const errorData = await response.json();
        if (errorData?.detail) {
          errorMessage = typeof errorData.detail === 'string'
            ? errorData.detail
            : JSON.stringify(errorData.detail);
        } else if (errorData?.message) {
          errorMessage = errorData.message;
        } else if (errorData?.error) {
          errorMessage = typeof errorData.error === 'string' ? errorData.error : JSON.stringify(errorData.error);
        }
      } catch {
        const text = await response.text();
        if (text) {
          errorMessage = text.slice(0, 200);
        }
      }

      if (response.status === 404) {
        throw new ApiError(errorMessage || 'Resource not found', 404);
      }
      if (response.status === 500) {
        throw new ApiError(errorMessage || 'Backend internal server error', 500);
      }
      throw new ApiError(errorMessage, response.status);
    }

    if (response.status === 204) {
      return {} as T;
    }

    return await response.json();
  } catch (error: unknown) {
    clearTimeout(timeoutId);

    if (error instanceof ApiError) {
      throw error;
    }

    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('Request timed out. The backend took too long to respond.', 408, false);
    }

    const errorMsg = error instanceof Error ? error.message : 'Unknown network error';
    throw new ApiError(
      `Cannot connect to backend at ${baseUrl}. Ensure the FastAPI server is running. (${errorMsg})`,
      undefined,
      true
    );
  }
}

export const api = {
  /**
   * Check backend availability
   */
  async checkHealth(): Promise<HealthCheckResponse> {
    return request<HealthCheckResponse>('/health', { method: 'GET' });
  },

  /**
   * Retrieve conversation list with normalized fields
   */
  async getConversations(): Promise<Conversation[]> {
    const res = await request<unknown>('/api/conversations', { method: 'GET' });
    let rawList: Record<string, unknown>[] = [];
    if (Array.isArray(res)) {
      rawList = res as Record<string, unknown>[];
    } else if (res && typeof res === 'object') {
      const record = res as Record<string, unknown>;
      if (Array.isArray(record.conversations)) {
        rawList = record.conversations as Record<string, unknown>[];
      } else if (Array.isArray(record.data)) {
        rawList = record.data as Record<string, unknown>[];
      }
    }
    return rawList.map((c) => {
      const count =
        typeof c.messages_count === 'number'
          ? c.messages_count
          : typeof c.message_count === 'number'
          ? c.message_count
          : 0;
      return {
        id: (c.id as string) || (c.conversation_id as string),
        title: (c.title as string) || 'Conversation',
        created_at: (c.created_at as string) || undefined,
        updated_at: (c.updated_at as string) || undefined,
        mode: (c.mode as IntelligenceMode) || 'balanced',
        context_summary: (c.summary as string) || (c.context_summary as string) || null,
        messages_count: count,
        messages_in_context: typeof c.messages_in_context === 'number' ? c.messages_in_context : count,
      };
    });
  },

  /**
   * Create a conversation with title and initial mode
   */
  async createConversation(title?: string, mode: IntelligenceMode = 'balanced'): Promise<Conversation> {
    const payload: Record<string, unknown> = {
      mode,
    };
    if (title) payload.title = title;
    const res = await request<Record<string, unknown>>('/api/conversations', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    const convId = (res.id as string) || (res.conversation_id as string);
    return {
      id: convId,
      title: (res.title as string) || title || 'New Conversation',
      created_at: (res.created_at as string) || new Date().toISOString(),
      mode: (res.mode as IntelligenceMode) || mode,
      messages_count: 0,
      messages_in_context: 0,
      messages: [],
    };
  },

  /**
   * Retrieve conversation history
   */
  async getConversation(id: string): Promise<{
    conversation: Conversation;
    messages: Message[];
  }> {
    const res = await request<unknown>(`/api/conversations/${encodeURIComponent(id)}`, {
      method: 'GET',
    });

    if (Array.isArray(res)) {
      return {
        conversation: { id, title: 'Chat', mode: 'balanced', messages_count: res.length },
        messages: res as Message[],
      };
    }

    if (res && typeof res === 'object') {
      const data = res as Record<string, unknown>;
      const rawMessages: Record<string, unknown>[] = Array.isArray(data.messages)
        ? (data.messages as Record<string, unknown>[])
        : [];

      const messages: Message[] = rawMessages.map((m) => ({
        id: String(m.id || ''),
        role: (m.role as 'user' | 'assistant') || 'user',
        content: (m.content as string) || '',
        created_at: (m.created_at as string) || undefined,
        mode: (m.mode as IntelligenceMode) || undefined,
        model_label: (m.model_label as string) || undefined,
      }));

      const convId = (data.id as string) || (data.conversation_id as string) || id;
      const conversation: Conversation = {
        id: convId,
        title: (data.title as string) || 'Conversation',
        created_at: (data.created_at as string) || undefined,
        updated_at: (data.updated_at as string) || undefined,
        mode: (data.mode as IntelligenceMode) || 'balanced',
        messages_in_context:
          typeof data.messages_in_context === 'number' ? data.messages_in_context : messages.length,
        context_summary:
          typeof data.summary === 'string'
            ? data.summary
            : typeof data.context_summary === 'string'
            ? data.context_summary
            : null,
        messages_count: messages.length,
        messages,
      };

      return { conversation, messages };
    }

    return {
      conversation: { id, title: 'Chat', mode: 'balanced', messages_count: 0 },
      messages: [],
    };
  },

  /**
   * Update intelligence mode for a conversation
   */
  async updateConversationMode(id: string, mode: IntelligenceMode): Promise<Conversation> {
    const res = await request<Record<string, unknown>>(`/api/conversations/${encodeURIComponent(id)}/mode`, {
      method: 'PATCH',
      body: JSON.stringify({ mode }),
    });
    const convId = (res.id as string) || (res.conversation_id as string) || id;
    return {
      id: convId,
      title: (res.title as string) || 'Conversation',
      mode: (res.mode as IntelligenceMode) || mode,
      created_at: (res.created_at as string) || undefined,
      updated_at: (res.updated_at as string) || undefined,
    };
  },

  /**
   * Delete a conversation
   */
  async deleteConversation(id: string): Promise<void> {
    await request<unknown>(`/api/conversations/${encodeURIComponent(id)}`, {
      method: 'DELETE',
    });
  },

  /**
   * Send a message and receive an AI response with selected mode
   */
  async sendMessage(conversationId: string, message: string, mode: IntelligenceMode = 'balanced'): Promise<ChatResponse> {
    const res = await request<ChatResponse>('/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        conversation_id: conversationId,
        message,
        mode,
      }),
    });
    return {
      conversation_id: res.conversation_id,
      reply: res.reply,
      mode: res.mode || mode,
      model_label: res.model_label,
      context_summary: res.context_summary,
      messages_in_context: res.messages_in_context,
    };
  },
};
