import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Copy, Check, RotateCcw, AlertTriangle, Sparkles, User } from 'lucide-react';
import { Message } from '../types';

interface ChatMessageProps {
  message: Message;
  isError?: boolean;
  onRetry?: () => void;
  isLoading?: boolean;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  isError = false,
  onRetry,
  isLoading = false,
}) => {
  const [copiedMessage, setCopiedMessage] = useState(false);
  const isUser = message.role === 'user';

  const copyText = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedMessage(true);
    setTimeout(() => setCopiedMessage(false), 2000);
  };

  return (
    <div
      className={`group w-full py-5 px-4 md:px-6 transition-colors ${
        isUser ? 'bg-transparent' : 'bg-app-main'
      }`}
    >
      <div className="max-w-3xl mx-auto flex items-start gap-4">
        {/* Avatar */}
        <div
          className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5 border text-xs bg-app-composer border-app-subtle text-app-primary`}
        >
          {isUser ? <User className="w-3.5 h-3.5" /> : <Sparkles className="w-3.5 h-3.5" />}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0 space-y-2">
          {/* Header label */}
          <div className="flex items-center justify-between text-xs text-app-muted">
            <div className="flex items-center gap-1.5">
              <span className="font-medium text-app-primary">{isUser ? 'You' : 'ContextAI'}</span>
              {!isUser && (message.model_label || message.mode) && (
                <span className="text-[11px] text-app-muted">
                  · {message.model_label || (message.mode === 'swift' ? 'Swift' : message.mode === 'deep' ? 'Deep' : 'Balanced')}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                onClick={() => copyText(message.content)}
                className="flex items-center gap-1 hover:text-app-primary transition-colors cursor-pointer"
                title="Copy message"
              >
                {copiedMessage ? (
                  <>
                    <Check className="w-3 h-3 text-emerald-500" />
                    <span>Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3" />
                    <span>Copy</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Message body */}
          {isUser ? (
            <div className="text-app-primary text-sm md:text-base leading-relaxed whitespace-pre-wrap break-words">
              {message.content}
            </div>
          ) : (
            <div className="text-app-primary text-sm md:text-base leading-relaxed markdown-content break-words">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  code({ className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || '');
                    const codeString = String(children).replace(/\n$/, '');
                    const isInline = !className && !String(children).includes('\n');

                    if (isInline) {
                      return (
                        <code
                          className="bg-app-surface text-app-primary px-1.5 py-0.5 rounded font-mono text-xs border border-app-subtle"
                          {...props}
                        >
                          {children}
                        </code>
                      );
                    }

                    return (
                      <CodeBlock
                        code={codeString}
                        language={match ? match[1] : 'code'}
                      />
                    );
                  },
                  p({ children }) {
                    return <p className="mb-3 last:mb-0 leading-relaxed text-app-primary">{children}</p>;
                  },
                  ul({ children }) {
                    return <ul className="list-disc pl-5 mb-3 space-y-1 text-app-primary">{children}</ul>;
                  },
                  ol({ children }) {
                    return <ol className="list-decimal pl-5 mb-3 space-y-1 text-app-primary">{children}</ol>;
                  },
                  li({ children }) {
                    return <li className="leading-relaxed">{children}</li>;
                  },
                  h1({ children }) {
                    return <h1 className="text-xl font-bold text-app-primary mt-4 mb-2">{children}</h1>;
                  },
                  h2({ children }) {
                    return <h2 className="text-lg font-semibold text-app-primary mt-3 mb-2">{children}</h2>;
                  },
                  h3({ children }) {
                    return <h3 className="text-base font-semibold text-app-primary mt-2 mb-1">{children}</h3>;
                  },
                  blockquote({ children }) {
                    return (
                      <blockquote className="border-l-2 border-app-subtle pl-3 italic text-app-secondary my-3">
                        {children}
                      </blockquote>
                    );
                  },
                  table({ children }) {
                    return (
                      <div className="overflow-x-auto my-3 border border-app-subtle rounded">
                        <table className="w-full text-left text-xs text-app-secondary divide-y divide-app-subtle">
                          {children}
                        </table>
                      </div>
                    );
                  },
                  th({ children }) {
                    return <th className="px-3 py-2 bg-app-surface text-app-primary font-medium">{children}</th>;
                  },
                  td({ children }) {
                    return <td className="px-3 py-2 border-t border-app-subtle">{children}</td>;
                  },
                  a({ href, children }) {
                    return (
                      <a
                        href={href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-app-primary underline hover:text-app-secondary transition-colors"
                      >
                        {children}
                      </a>
                    );
                  },
                }}
              >
                {message.content}
              </ReactMarkdown>

              {/* Error indicator */}
              {isError && (
                <div className="mt-3 p-3 bg-app-error border border-app-error rounded-lg flex items-center justify-between text-xs text-app-error">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 shrink-0 text-red-500" />
                    <span>Failed to get complete response from backend.</span>
                  </div>
                  {onRetry && (
                    <button
                      onClick={onRetry}
                      className="flex items-center gap-1.5 px-2.5 py-1 bg-app-surface hover:bg-app-composer text-app-primary rounded transition-colors border border-app-subtle cursor-pointer"
                    >
                      <RotateCcw className="w-3 h-3" />
                      <span>Retry</span>
                    </button>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Messages in context and mode indicator if provided */}
          {!isUser && (typeof message.messages_in_context === 'number' || message.mode || message.model_label) && (
            <div className="pt-1 text-[11px] text-app-muted flex items-center gap-3">
              {typeof message.messages_in_context === 'number' && (
                <span>{message.messages_in_context} messages in context</span>
              )}
              {message.mode && (
                <span>
                  Mode: <span className="capitalize text-app-secondary">{message.model_label || message.mode}</span>
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

interface CodeBlockProps {
  code: string;
  language: string;
}

const CodeBlock: React.FC<CodeBlockProps> = ({ code, language }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="my-3 rounded-lg border border-app-subtle bg-app-code overflow-hidden text-xs">
      <div className="flex items-center justify-between px-3.5 py-1.5 bg-app-code-header border-b border-app-subtle text-app-muted">
        <span className="font-mono text-[11px] uppercase tracking-wider">{language}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 hover:text-app-primary transition-colors cursor-pointer"
          title="Copy code"
        >
          {copied ? (
            <>
              <Check className="w-3 h-3 text-emerald-500" />
              <span>Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3 h-3" />
              <span>Copy code</span>
            </>
          )}
        </button>
      </div>
      <div className="p-3.5 overflow-x-auto font-mono text-[13px] text-app-primary leading-relaxed">
        <pre>{code}</pre>
      </div>
    </div>
  );
};
