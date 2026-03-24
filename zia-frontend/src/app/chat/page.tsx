"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useChat } from "@/context/ChatContext";
import { ChatWindow } from "@/components/ChatWindow";
import { MessageInput } from "@/components/MessageInput";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";

export default function ChatPage() {
  const router = useRouter();
  const {
    profile,
    sessionId,
    messages,
    isLoading,
    isSendingMessage,
    error,
    sendMessage,
    resetChat,
    clearError,
    conversations,
    loadConversations,
    loadConversationMessages,
  } = useChat();

  // Redirect to home if no profile
  useEffect(() => {
    if (!profile) {
      router.push("/");
      return;
    }

    // Load conversations on mount
    if (conversations === null && profile.phone) {
      loadConversations(profile.phone);
    }

    // Auto-load most recent conversation if no current session
    if (!sessionId && conversations && conversations.length > 0) {
      const mostRecent = conversations[0];
      loadConversationMessages(mostRecent.id);
    }
  }, [profile, router, conversations, sessionId, loadConversations, loadConversationMessages]);

  if (!profile) {
    return (
      <div className="flex items-center justify-center h-screen">
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-white">
      {/* Sidebar - Conversation History */}
      <div className="hidden md:flex md:w-64 flex-col bg-slate-50 border-r border-slate-200">
        {/* Sidebar Header */}
        <div className="p-4 border-b border-slate-200 bg-white">
          <h2 className="text-sm font-semibold text-slate-900">Conversations</h2>
        </div>

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto p-3 space-y-1">
          {conversations && conversations.length > 0 ? (
            conversations.slice(0, 10).map((conv) => (
              <button
                key={conv.id}
                onClick={() => loadConversationMessages(conv.id)}
                className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-all duration-200 truncate ${
                  sessionId === conv.id
                    ? "bg-blue-50 text-slate-900 font-medium border border-slate-300"
                    : "text-slate-700 hover:bg-slate-100"
                }`}
                title={conv.id}
              >
                <div className="truncate">Chat {new Date(conv.started_at).toLocaleDateString()}</div>
                <div className="text-xs text-slate-500 mt-0.5">{conv.turn_count} turns</div>
              </button>
            ))
          ) : (
            <div className="text-center py-8 text-slate-500 text-sm">
              <p>No conversations yet</p>
            </div>
          )}
        </div>

        {/* Sidebar Footer */}
        <div className="p-4 border-t border-slate-200 space-y-2">
          <Link
            href="/history"
            className="flex items-center justify-center w-full px-3 py-2 text-sm font-medium text-slate-700 bg-white rounded-lg hover:bg-slate-100 transition-colors border border-slate-200"
          >
            History
          </Link>
          <Link
            href="/profile"
            className="flex items-center justify-center w-full px-3 py-2 text-sm font-medium text-slate-700 bg-white rounded-lg hover:bg-slate-100 transition-colors border border-slate-200"
          >
            Profile
          </Link>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white border-b border-slate-200 px-6 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Link href="/" className="md:hidden p-2 hover:bg-slate-100 rounded-lg transition-colors">
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div>
                <h1 className="text-xl font-semibold text-slate-900">
                  Zia
                </h1>
                <p className="text-xs text-slate-500">Career companion</p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-sm font-medium text-slate-900">{profile.name}</p>
              <p className="text-xs text-slate-500">{profile.phone}</p>
            </div>
          </div>
        </div>

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto w-full">
          {/* Messages container full width */}
          <div className="px-6 py-8 w-full h-full flex flex-col">
            {messages.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center space-y-6 py-12 max-w-2xl mx-auto">
                <div className="w-12 h-12 bg-slate-100 rounded-full flex items-center justify-center">
                  <span className="text-2xl font-semibold text-slate-900">Z</span>
                </div>
                <div className="space-y-2">
                  <h2 className="text-2xl font-semibold text-slate-900">Welcome to Zia</h2>
                  <p className="text-slate-600">
                    Your AI career companion. Ask me anything about opportunities, salaries, or career growth.
                  </p>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-6 w-full">
                  <button
                    onClick={() =>
                      sendMessage(
                        "What salary should I expect for my role and experience?"
                      )
                    }
                    className="p-3 text-sm bg-white border border-slate-200 rounded-lg hover:bg-slate-50 text-slate-700 font-medium transition-colors"
                  >
                    Salary Guidance
                  </button>
                  <button
                    onClick={() =>
                      sendMessage(
                        "How can I grow in my career path?"
                      )
                    }
                    className="p-3 text-sm bg-white border border-slate-200 rounded-lg hover:bg-slate-50 text-slate-700 font-medium transition-colors"
                  >
                    Career Growth
                  </button>
                  <button
                    onClick={() =>
                      sendMessage(
                        "What companies match my profile?"
                      )
                    }
                    className="p-3 text-sm bg-white border border-slate-200 rounded-lg hover:bg-slate-50 text-slate-700 font-medium transition-colors"
                  >
                    Company Match
                  </button>
                  <button
                    onClick={() =>
                      sendMessage(
                        "How do I handle a new job offer?"
                      )
                    }
                    className="p-3 text-sm bg-white border border-slate-200 rounded-lg hover:bg-slate-50 text-slate-700 font-medium transition-colors"
                  >
                    Job Offer Help
                  </button>
                </div>
              </div>
            ) : (
              <ChatWindow
                messages={messages}
                sessionId={sessionId}
                isLoading={isSendingMessage}
              />
            )}
          </div>
        </div>

        {/* Input Area */}
        <div className="bg-white border-t border-slate-200 px-6 py-4">
          <div className="w-full max-w-none">
            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start justify-between gap-3 animate-slide-in">
                <div>
                  <p className="text-sm font-medium text-red-900">Error</p>
                  <p className="text-sm text-red-800">{error}</p>
                </div>
                <button
                  onClick={clearError}
                  className="text-red-600 hover:text-red-700 font-medium text-sm"
                >
                  ✕
                </button>
              </div>
            )}
            <MessageInput
              onSend={sendMessage}
              isLoading={isSendingMessage}
              disabled={isLoading}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
