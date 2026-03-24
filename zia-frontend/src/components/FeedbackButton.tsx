"use client";

import { useState } from "react";
import { ThumbsUp, ThumbsDown } from "lucide-react";
import { useChat } from "@/context/ChatContext";

interface FeedbackButtonProps {
  sessionId: string;
  turnNumber: number;
  currentFeedback: "up" | "down" | null;
  onFeedbackSubmitted?: () => void;
}

export function FeedbackButton({
  sessionId,
  turnNumber,
  currentFeedback,
  onFeedbackSubmitted,
}: FeedbackButtonProps) {
  const { submitFeedback, error } = useChat();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [localFeedback, setLocalFeedback] = useState<"up" | "down" | null>(
    currentFeedback
  );

  const handleFeedback = async (rating: "up" | "down") => {
    try {
      setIsSubmitting(true);
      await submitFeedback(sessionId, turnNumber, rating);
      setLocalFeedback(rating);
      onFeedbackSubmitted?.();
    } catch (err) {
      console.error("Failed to submit feedback:", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={() => handleFeedback("up")}
        disabled={isSubmitting}
        className={`p-1.5 rounded transition-colors ${
          localFeedback === "up"
            ? "bg-green-100 text-green-600"
            : "text-gray-400 hover:text-green-600 hover:bg-green-50"
        } disabled:opacity-50 disabled:cursor-not-allowed`}
        title="Helpful response"
      >
        <ThumbsUp className="w-4 h-4" />
      </button>
      <button
        onClick={() => handleFeedback("down")}
        disabled={isSubmitting}
        className={`p-1.5 rounded transition-colors ${
          localFeedback === "down"
            ? "bg-red-100 text-red-600"
            : "text-gray-400 hover:text-red-600 hover:bg-red-50"
        } disabled:opacity-50 disabled:cursor-not-allowed`}
        title="Not helpful"
      >
        <ThumbsDown className="w-4 h-4" />
      </button>
    </div>
  );
}
