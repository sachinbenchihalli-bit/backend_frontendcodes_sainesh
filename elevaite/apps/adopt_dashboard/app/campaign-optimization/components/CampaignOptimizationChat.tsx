"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { Send, Bot, User, Zap, AlertCircle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { backendApi } from "@/services/backendApi";
import { ChatMessage } from "@/types";
import { ProgressiveMarkdown } from "./ProgressiveMarkdown";
import "./CampaignOptimizationChat.scss";
import "katex/dist/katex.min.css";

const mathConfig = { singleDollarTextMath: false };

interface Campaign {
  id: string;
  name: string;
  status: string;
  brand?: string;
  budget?: number;
  impressions_delivered?: number;
  clicks?: number;
  ctr?: number;
  roas?: number;
}

interface ChatMessageWithSuggestions extends ChatMessage {
  suggestions?: string[];
  isStreaming?: boolean;
}

interface CampaignOptimizationChatProps {
  campaign: Campaign;
  autoAnalyze?: boolean;
}

export function CampaignOptimizationChat({ campaign, autoAnalyze = false }: CampaignOptimizationChatProps) {
  const [chatMessages, setChatMessages] = useState<ChatMessageWithSuggestions[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(() => `session_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`);
  const [backendError, setBackendError] = useState<string | null>(null);
  const [hasAutoAnalyzed, setHasAutoAnalyzed] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // ─────────────────────────────────────────────────────────────────────────────
  // SCROLL STRATEGY
  //
  // The root cause of the "scroll fight" was two things working against each other:
  //
  //  1. scrollIntoView({ behavior: "smooth" }) has its OWN animation that
  //     continues running even after the user manually scrolls. Every new token
  //     re-triggers it, so the smooth animation repeatedly yanks the user back
  //     to the bottom — they can never win.
  //
  //  2. The "am I near the bottom?" check ran AFTER React re-rendered, by which
  //     point the container's scrollHeight had already grown, making the
  //     distanceFromBottom stale.
  //
  // THE FIX:
  //  - Replace scrollIntoView with direct scrollTop assignment (instant, no
  //    animation that fights the user).
  //  - Track user intent via a ref set synchronously in onScroll — no stale
  //    closure issues.
  //  - "Pinned to bottom" = user never manually scrolled, OR they scrolled
  //    back to within SCROLL_THRESHOLD px of the bottom.
  //  - Once user scrolls up more than SCROLL_THRESHOLD px → stop all
  //    auto-scroll for the rest of this streaming response.
  //  - When user sends a NEW message → force-scroll to bottom and re-enable.
  // ─────────────────────────────────────────────────────────────────────────────

  const SCROLL_THRESHOLD = 60; // px from bottom = "close enough to pin"

  // true  = auto-scroll is active (user is at bottom or hasn't scrolled yet)
  // false = user scrolled up — leave them alone
  const pinnedToBottom = useRef(true);

  // Tracks whether the LAST scroll event was triggered by our own code (so we
  // don't mistake our own programmatic scroll for a user scroll).
  const programmaticScroll = useRef(false);

  // ── Scroll the container to the very bottom instantly (no animation) ───────
  const scrollToBottom = useCallback(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    programmaticScroll.current = true;
    el.scrollTop = el.scrollHeight; // instant — no smooth, no fight
  }, []);

  // ── Called on every scroll event inside the messages container ─────────────
  const handleScroll = useCallback(() => {
    // If WE triggered this scroll, ignore it — it's not a user gesture
    if (programmaticScroll.current) {
      programmaticScroll.current = false;
      return;
    }

    const el = scrollContainerRef.current;
    if (!el) return;

    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;

    if (distanceFromBottom <= SCROLL_THRESHOLD) {
      // User scrolled back to the bottom — re-enable pinning
      pinnedToBottom.current = true;
    } else {
      // User scrolled UP — stop auto-scroll immediately and don't touch again
      pinnedToBottom.current = false;
    }
  }, []);

  // ── PREWARM on mount ──────────────────────────────────────────────────────
  useEffect(() => {
    if (campaign.id) {
      backendApi.prewarmCampaignContext(campaign.id);
    }
  }, [campaign.id]);

  // ── Auto-scroll on new content — only when pinned ────────────────────────
  // Runs after every render caused by chatMessages changing (i.e. every token).
  // We use `el.scrollTop = el.scrollHeight` (instant) not scrollIntoView
  // (smooth), so it never fights a user scroll-up gesture.
  useEffect(() => {
    if (pinnedToBottom.current) {
      scrollToBottom();
    }
  }, [chatMessages, scrollToBottom]);

  // ── CORE STREAMING SEND ───────────────────────────────────────────────────
  const sendMessageStreaming = async (message: string) => {
    const userMessage: ChatMessageWithSuggestions = {
      id: Date.now(),
      text: message,
      sender: "user",
      timestamp: new Date(),
    };
    setChatMessages((prev) => [...prev, userMessage]);
    setChatInput("");
    setIsLoading(true);
    setBackendError(null);

    // New message sent → re-enable pinning and jump to bottom
    pinnedToBottom.current = true;
    scrollToBottom();

    const botMessageId = Date.now() + 1;
    setChatMessages((prev) => [
      ...prev,
      { id: botMessageId, text: "", sender: "bot", timestamp: new Date(), isStreaming: true },
    ]);

    try {
      await backendApi.sendCampaignOptimizationMessageStream(
        campaign.id,
        message,
        sessionId,
        {
          onChunk: (text: string) => {
            setChatMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last?.id === botMessageId) {
                return [...updated.slice(0, -1), { ...last, text: last.text + text, isStreaming: true }];
              }
              return updated;
            });
          },

          onFollowupPrompts: (prompts: string[]) => {
            setChatMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last?.id === botMessageId) {
                return [...updated.slice(0, -1), { ...last, suggestions: prompts, isStreaming: false }];
              }
              return updated;
            });
          },

          onDone: () => {
            setChatMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last?.id === botMessageId) {
                return [...updated.slice(0, -1), { ...last, isStreaming: false }];
              }
              return updated;
            });
            setIsLoading(false);
          },

          onError: (error: string) => {
            setChatMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last?.id === botMessageId) {
                return [
                  ...updated.slice(0, -1),
                  {
                    ...last,
                    text: `I'm having trouble connecting to the optimization service. Please try again.\n\nError: ${error}`,
                    isStreaming: false,
                    error: "Service error",
                  },
                ];
              }
              return updated;
            });
            setBackendError(error);
            setIsLoading(false);
          },

          // Tools run silently — no UI labels
          onToolStart: (_toolName: string) => { /* intentionally silent */ },
          onToolDone: (_toolName: string, _source: "cache" | "live") => { /* intentionally silent */ },
        }
      );
    } catch (error) {
      const errMsg = error instanceof Error ? error.message : "Failed to send message";
      setBackendError(errMsg);
      setChatMessages((prev) => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last?.id === botMessageId) {
          return [
            ...updated.slice(0, -1),
            {
              ...last,
              text: `I'm having trouble connecting to the optimization service. Please try again.\n\nError: ${errMsg}`,
              isStreaming: false,
              error: "Service error",
            },
          ];
        }
        return updated;
      });
      setIsLoading(false);
    }
  };

  // ── AUTO-ANALYZE ──────────────────────────────────────────────────────────
  useEffect(() => {
    const triggerAutoAnalysis = async () => {
      if (autoAnalyze && campaign.id && !hasAutoAnalyzed && !isLoading) {
        setHasAutoAnalyzed(true);
        await sendMessageStreaming("Provide a performance summary for this campaign.");
      }
    };
    const timer = setTimeout(triggerAutoAnalysis, 100);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoAnalyze, campaign.id, hasAutoAnalyzed]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => setChatInput(e.target.value);
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !isLoading && chatInput.trim()) handleSendMessage();
  };
  const handleSuggestionClick = (suggestion: string) => sendMessageStreaming(suggestion);
  const handleSendMessage = async (messageText?: string) => {
    const message = messageText || chatInput.trim();
    if (!message || isLoading) return;
    await sendMessageStreaming(message);
  };

  const renderUserAvatar = () => <div className="message-avatar user-avatar"><User size={16} /></div>;
  const renderBotAvatar = () => <div className="message-avatar bot-avatar"><Bot size={16} /></div>;

  // ── RENDER ────────────────────────────────────────────────────────────────
  return (
    <Card className="h-[200] flex flex-col bg-white shadow-sm border border-gray-200">
      <CardContent className="p-0 flex flex-col h-full">

        {/* Header */}
        <div className="border-b border-gray-200 p-4">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-gradient-to-r from-orange-500 to-pink-500 rounded-lg flex items-center justify-center">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">
                {campaign?.status?.toLowerCase() === "completed"
                  ? "Campaign Analysis Assistant"
                  : "Campaign Intelligence Assistant"}
              </h3>
              <p className="text-sm text-gray-600">
                {backendError
                  ? "Service temporarily unavailable"
                  : campaign?.status?.toLowerCase() === "completed"
                  ? "AI-powered insights and performance analysis"
                  : "AI-Powered Campaign Insights and Recommendations"}
              </p>
            </div>
          </div>

          {backendError && (
            <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded-md">
              <div className="flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 text-red-500" />
                <span className="text-sm text-red-700">Connection issue: {backendError}</span>
              </div>
            </div>
          )}
        </div>

        {/* Messages */}
        <div className="campaign-chat-interface flex-1 flex flex-col">
          <div
            className="chat-messages-container flex-1"
            ref={scrollContainerRef}
            onScroll={handleScroll}
          >
            <div className="chat-messages">
              {chatMessages.map((message) => (
                <div key={message.id}>
                  <div className={`chat-message ${message.sender === "user" ? "user-message" : "bot-message"}`}>
                    {message.sender === "user" ? renderUserAvatar() : renderBotAvatar()}
                    <div className="message-bubble">
                      <div className="message-text">
                        {message.sender === "bot" ? (
                          <>
                            {/* "Thinking..." shown inside empty bubble before first token */}
                            {message.isStreaming && message.text === "" ? (
                              <div className="thinking-inline">
                                <span className="thinking-text">Thinking</span>
                                <span className="thinking-dots" aria-hidden>
                                  <span /><span /><span />
                                </span>
                              </div>
                            ) : (
                              <>
                                <ProgressiveMarkdown
                                  content={message.text}
                                  initialDelay={0}
                                  wordsPerTick={3}
                                  tickInterval={25}
                                />
                                {message.isStreaming && message.text !== "" && (
                                  <span className="streaming-cursor" aria-hidden />
                                )}
                              </>
                            )}
                          </>
                        ) : (
                          <ReactMarkdown
                            remarkPlugins={[[remarkMath, mathConfig], remarkGfm]}
                            rehypePlugins={[rehypeKatex]}
                            components={{
                              h1: ({ node, ...props }) => <h1 className="text-2xl font-extrabold pl-1.5 mt-1 mb-1" {...props} />,
                              h2: ({ node, ...props }) => <h2 className="text-xl font-bold pl-1.5 mt-1 mb-1" {...props} />,
                              h3: ({ node, ...props }) => <h3 className="text-lg font-semibold pl-1.5 mt-5 mb-1" {...props} />,
                              h4: ({ node, ...props }) => <h3 className="text-base font-semibold pl-1.5 mt-1 mb-1" {...props} />,
                              p: ({ node, ...props }) => <p className="font-normal mb-2 pl-2" {...props} />,
                              strong: ({ node, ...props }) => <strong className="font-semibold" {...props} />,
                              em: ({ node, ...props }) => <em className="italic" {...props} />,
                              ul: ({ node, ...props }) => <ul className="list-disc pl-5 ml-2 mt-1 mb-3 space-y-1 leading-tight" {...props} />,
                              ol: ({ node, ...props }) => <ol className="list-decimal pl-5 ml-2 my-1 space-y-1 leading-tight" {...props} />,
                              li: ({ node, ...props }) => <li className="m-0" {...props} />,
                              a: ({ href, children, ...props }) => (
                                <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-600 underline" {...props}>{children}</a>
                              ),
                              table: ({ node, ...props }) => <div className="overflow-x-auto"><table className="min-w-full text-sm" {...props} /></div>,
                              th: ({ node, ...props }) => <th className="border px-2 py-1 bg-gray-50" {...props} />,
                              td: ({ node, ...props }) => <td className="border px-2 py-1" {...props} />,
                              br: () => <br />,
                            }}
                          >
                            {message.text}
                          </ReactMarkdown>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Follow-up suggestions */}
                  {message.sender === "bot" &&
                    message.suggestions &&
                    message.suggestions.length > 0 &&
                    !message.isStreaming &&
                    !isLoading && (
                      <div className="mt-4 flex flex-col gap-2 max-w-md">
                        {message.suggestions.map((suggestion, sugIndex) => (
                          <button
                            key={sugIndex}
                            onClick={() => handleSuggestionClick(suggestion)}
                            disabled={isLoading}
                            className="text-left px-4 py-2 bg-gray-50 hover:bg-gray-100 border border-gray-300 rounded-lg text-sm text-gray-700 font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            {suggestion}
                          </button>
                        ))}
                      </div>
                    )}
                </div>
              ))}

              {/* Anchor div — used only as a measurement point, NOT for scrollIntoView */}
              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Input */}
          <div className="chat-input-container">
            <input
              type="text"
              value={chatInput}
              onChange={handleInputChange}
              onKeyDown={handleKeyPress}
              placeholder="Ask about campaign optimization..."
              className="chat-input"
              disabled={isLoading}
            />
            <button
              onClick={() => handleSendMessage()}
              className="chat-send-button"
              disabled={isLoading || !chatInput.trim()}
            >
              {isLoading ? "..." : <Send size={18} />}
            </button>
          </div>
        </div>
      </CardContent>

      <style>{`
        .streaming-cursor {
          display: inline-block;
          width: 2px;
          height: 1em;
          background: #FF681F;
          margin-left: 2px;
          vertical-align: middle;
          animation: blink-cursor 1s step-start infinite;
        }
        @keyframes blink-cursor {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }

        .thinking-inline {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 2px 4px;
        }
        .thinking-inline .thinking-text {
          font-size: 0.875rem;
          color: #6b7280;
          font-style: italic;
        }
        .thinking-inline .thinking-dots {
          display: flex;
          gap: 3px;
          align-items: center;
        }
        .thinking-inline .thinking-dots span {
          width: 5px;
          height: 5px;
          border-radius: 50%;
          background: #FF681F;
          animation: thinking-bounce 1.2s ease-in-out infinite;
        }
        .thinking-inline .thinking-dots span:nth-child(1) { animation-delay: 0s; }
        .thinking-inline .thinking-dots span:nth-child(2) { animation-delay: 0.2s; }
        .thinking-inline .thinking-dots span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes thinking-bounce {
          0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
          30%            { transform: translateY(-4px); opacity: 1; }
        }
      `}</style>
    </Card>
  );
}
