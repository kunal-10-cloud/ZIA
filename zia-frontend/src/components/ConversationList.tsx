"use client";

import { ConversationRecord } from "@/lib/types";
import { formatDistanceToNow, format } from "date-fns";
import { MessageSquare, Clock } from "lucide-react";

interface ConversationListProps {
  conversations: ConversationRecord[];
  selectedId?: string;
  onSelect: (id: string) => void;
}

export function ConversationList({
  conversations,
  selectedId,
  onSelect,
}: ConversationListProps) {
  if (!conversations || conversations.length === 0) {
    return (
      <div className="text-center text-gray-500 py-8">
        <MessageSquare className="w-12 h-12 mx-auto mb-2 opacity-50" />
        <p>No conversations yet.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {conversations.map((conv) => {
        const firstMessage = conv.messages?.[0]?.user_message || "No messages";
        const preview = firstMessage.substring(0, 50);
        const isSelected = selectedId === conv.id;

        return (
          <button
            key={conv.id}
            onClick={() => onSelect(conv.id)}
            className={`w-full text-left p-3 rounded-lg border transition-colors ${
              isSelected
                ? "border-blue-600 bg-blue-50"
                : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
            }`}
          >
            <div className="flex items-start justify-between gap-2 mb-1">
              <p className="font-medium text-gray-900 text-sm truncate">
                {preview}...
              </p>
              <span className="text-xs text-gray-500 flex-shrink-0">
                {conv.turn_count} turns
              </span>
            </div>
            <div className="flex items-center gap-1 text-xs text-gray-500">
              <Clock className="w-3 h-3" />
              <span>
                {formatDistanceToNow(new Date(conv.started_at), {
                  addSuffix: true,
                })}
              </span>
            </div>
          </button>
        );
      })}
    </div>
  );
}
