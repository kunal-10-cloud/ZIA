"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useChat } from "@/context/ChatContext";
import { ConversationList } from "@/components/ConversationList";
import { ChatWindow } from "@/components/ChatWindow";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";

export default function HistoryPage() {
  const router = useRouter();
  const {
    profile,
    conversations,
    isLoading,
    loadConversations,
    loadConversationMessages,
    messages,
  } = useChat();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Load conversations on mount
  useEffect(() => {
    if (!profile) {
      router.push("/");
      return;
    }

    if (!conversations) {
      loadConversations(profile.phone);
    }
  }, [profile, conversations, loadConversations, router]);

  const handleSelectConversation = async (id: string) => {
    setSelectedId(id);
    await loadConversationMessages(id);
  };

  if (!profile) {
    return (
      <div className="flex items-center justify-center h-96">
        <LoadingSpinner text="Loading..." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link
          href="/chat"
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <h1 className="text-3xl font-bold">Conversation History</h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Conversation List */}
        <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
          <h2 className="font-semibold text-gray-900 mb-4">
            {isLoading && conversations === null
              ? "Loading..."
              : `${conversations?.length || 0} Conversations`}
          </h2>
          {isLoading && conversations === null ? (
            <LoadingSpinner size="sm" text="Loading conversations..." />
          ) : (
            <ConversationList
              conversations={conversations || []}
              selectedId={selectedId || undefined}
              onSelect={handleSelectConversation}
            />
          )}
        </div>

        {/* Message Display */}
        <div className="md:col-span-2 bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
          {selectedId && messages.length > 0 ? (
            <>
              <h2 className="font-semibold text-gray-900 mb-4">
                Conversation Preview
              </h2>
              <ChatWindow messages={messages} sessionId={selectedId} />
            </>
          ) : (
            <div className="flex items-center justify-center h-96 text-gray-500">
              <p>
                {selectedId
                  ? "Loading conversation..."
                  : "Select a conversation to view"}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
