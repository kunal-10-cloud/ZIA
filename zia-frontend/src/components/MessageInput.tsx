"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Sparkles } from "lucide-react";

interface MessageInputProps {
  onSend: (message: string) => Promise<void>;
  isLoading?: boolean;
  disabled?: boolean;
}

export function MessageInput({
  onSend,
  isLoading = false,
  disabled = false,
}: MessageInputProps) {
  const [message, setMessage] = useState("");
  const [isSending, setIsSending] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || isSending || disabled || isLoading) return;

    setIsSending(true);
    try {
      await onSend(message);
      setMessage("");
      if (inputRef.current) {
        inputRef.current.focus();
        inputRef.current.style.height = "auto";
      }
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as any);
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMessage(e.target.value);
    // Auto-expand textarea
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height = Math.min(inputRef.current.scrollHeight, 150) + "px";
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full space-y-3">
      <div className="relative group">
        <div className="absolute inset-0 bg-gradient-to-r from-blue-400/20 to-indigo-400/20 rounded-lg blur opacity-0 group-focus-within:opacity-100 transition-opacity duration-300 -z-10"></div>
        <textarea
          ref={inputRef}
          value={message}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="Ask Zia anything about your career..."
          disabled={isSending || disabled || isLoading}
          rows={1}
          className="w-full px-4 py-3.5 text-base text-slate-900 placeholder-slate-400 bg-white border border-slate-200 rounded-lg shadow-sm resize-none transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-slate-50 disabled:cursor-not-allowed"
        />
      </div>
      <div className="flex items-center justify-between">
        <p className="text-xs text-slate-500">
          Press <kbd className="px-1.5 py-0.5 bg-slate-100 border border-slate-200 rounded text-slate-700 font-mono text-xs">Shift+Enter</kbd> for new line
        </p>
        <button
          type="submit"
          disabled={isSending || disabled || isLoading || !message.trim()}
          className="px-5 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-medium rounded-lg hover:from-blue-700 hover:to-indigo-700 disabled:from-slate-400 disabled:to-slate-500 disabled:cursor-not-allowed transition-all duration-200 flex items-center gap-2 shadow-md hover:shadow-lg disabled:shadow-none"
        >
          {isSending || isLoading ? (
            <>
              <Sparkles className="w-4 h-4 animate-spin" />
              Thinking...
            </>
          ) : (
            <>
              <Send className="w-4 h-4" />
              Send
            </>
          )}
        </button>
      </div>
    </form>
  );
}
