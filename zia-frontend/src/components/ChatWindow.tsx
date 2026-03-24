"use client";

import { useEffect, useRef } from "react";
import { MessageRecord } from "@/lib/types";
import { formatDistanceToNow } from "date-fns";
import { FeedbackButton } from "./FeedbackButton";

interface ChatWindowProps {
  messages: MessageRecord[];
  sessionId: string | null;
  isLoading?: boolean;
}

export function ChatWindow({
  messages,
  sessionId,
  isLoading = false,
}: ChatWindowProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex items-center justify-center h-96 text-gray-500">
        <p className="text-center">
          Start a conversation with Zia by sending a message below.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 w-full">
      {messages.map((message, index) => (
        <div key={message.turn} className="animate-slide-in space-y-2">
          {/* User Message */}
          <div className="flex justify-end mb-4">
            <div className="max-w-lg bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-2xl rounded-tr-sm px-5 py-3 shadow-sm hover:shadow-md transition-shadow">
              <p className="text-sm leading-relaxed">{message.user_message}</p>
            </div>
          </div>

          {/* Zia Response */}
          <div className="flex justify-start mb-3">
            <div className="max-w-lg bg-slate-100 border border-slate-200 rounded-2xl rounded-tl-sm px-5 py-3 shadow-sm hover:shadow-md transition-shadow">
              <p className="text-sm text-slate-900 leading-relaxed whitespace-pre-wrap">{message.zia_response}</p>
              <div className="flex items-center justify-between gap-3 mt-3 pt-2 border-t border-slate-300">
                {message.active_skill && (
                  <span className="text-xs text-slate-600 px-2 py-1 bg-slate-200 rounded-full">
                    {message.active_skill}
                  </span>
                )}
                {sessionId && (
                  <FeedbackButton
                    sessionId={sessionId}
                    turnNumber={message.turn}
                    currentFeedback={message.feedback}
                  />
                )}
              </div>
            </div>
          </div>
        </div>
      ))}

      {isLoading && (
        <div className="flex justify-start animate-slide-in">
          <div className="bg-slate-100 border border-slate-200 rounded-2xl rounded-tl-sm px-5 py-3">
            <div className="flex gap-2">
              <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" />
              <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "0.1s" }} />
              <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "0.2s" }} />
            </div>
          </div>
        </div>
      )}

      <div ref={messagesEndRef} />
    </div>
  );
}
