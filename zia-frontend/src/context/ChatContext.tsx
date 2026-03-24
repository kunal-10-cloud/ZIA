"use client";

/**
 * Zia Frontend — Chat Context
 * ============================
 * Global state management using React Context API.
 */

import {
  createContext,
  useContext,
  useState,
  ReactNode,
  useCallback,
} from "react";
import {
  CompanionProfile,
  CreateProfileRequest,
  UpdateProfileRequest,
  ChatState,
  AppContextType,
  MessageRecord,
  ConversationRecord,
} from "@/lib/types";
import { candidateAPI, chatAPI, APIError } from "@/lib/api";

// ─── Context Creation ──────────────────────────────────────────────────────

const ChatContext = createContext<AppContextType | undefined>(undefined);

// ─── Initial State ────────────────────────────────────────────────────────

const initialState: ChatState = {
  profile: null,
  sessionId: null,
  messages: [],
  isLoading: false,
  error: null,
  isSendingMessage: false,
};

// ─── Provider Component ────────────────────────────────────────────────────

export function ChatProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<CompanionProfile | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageRecord[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSendingMessage, setIsSendingMessage] = useState(false);
  const [conversations, setConversations] = useState<ConversationRecord[] | null>(
    null
  );

  // ─── Profile Actions ────────────────────────────────────────────────────

  const createOrGetProfile = useCallback(
    async (phone: string, name: string) => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await candidateAPI.createOrGetProfile({ phone, name });
        setProfile(result);
        // Store phone in localStorage for persistence
        if (typeof window !== "undefined") {
          localStorage.setItem("zia_phone", phone);
        }
      } catch (err) {
        const message =
          err instanceof APIError ? err.message : "Failed to create profile";
        setError(message);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const getProfile = useCallback(async (phone: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await candidateAPI.getProfile(phone);
      setProfile(result);
    } catch (err) {
      const message =
        err instanceof APIError ? err.message : "Failed to fetch profile";
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const updateProfile = useCallback(async (data: UpdateProfileRequest) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await candidateAPI.updateProfile(data);
      setProfile(result);
    } catch (err) {
      const message =
        err instanceof APIError ? err.message : "Failed to update profile";
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  // ─── Chat Actions ───────────────────────────────────────────────────────

  const sendMessage = useCallback(async (message: string) => {
    setIsSendingMessage(true);
    setError(null);
    try {
      const response = await chatAPI.sendMessage({
        message,
        session_id: sessionId || undefined,
        phone: profile?.phone || undefined,
      });

      const newSessionId = response.session_id;
      
      // Set session ID if new
      if (!sessionId) {
        setSessionId(newSessionId);
        
        // Add new conversation to the list (for a new chat)
        const newConversation: ConversationRecord = {
          id: newSessionId,
          candidate_id: profile?.id || "",
          channel: "web",
          started_at: new Date().toISOString(),
          ended_at: null,
          turn_count: 1,
          relationship_stage_at_start: profile?.relationship_stage || 1,
          messages: [],
          created_at: new Date().toISOString(),
        };
        
        setConversations((prev) => {
          if (!prev) return [newConversation];
          return [newConversation, ...prev];
        });
      }

      // Add user message to transcript
      setMessages((prev) => [
        ...prev,
        {
          turn: response.turn_number,
          user_message: message,
          zia_response: response.response,
          active_skill: response.active_skill || "",
          timestamp: response.timestamp,
          feedback: null,
        },
      ]);

      // Update conversation turn count
      setConversations((prev) => {
        if (!prev) return prev;
        return prev.map((conv) =>
          conv.id === newSessionId
            ? { ...conv, turn_count: response.turn_number }
            : conv
        );
      });
    } catch (err) {
      const errorMsg =
        err instanceof APIError ? err.message : "Failed to send message";
      setError(errorMsg);
      throw err;
    } finally {
      setIsSendingMessage(false);
    }
  }, [sessionId, profile?.phone, profile?.id, profile?.relationship_stage]);

  const resetChat = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      // Clear current session and messages
      setSessionId(null);
      setMessages([]);
      
      // Reload conversations to show full list
      if (profile?.phone) {
        const conversations = await candidateAPI.getConversations(profile.phone);
        setConversations(conversations);
      }
    } catch (err) {
      const message =
        err instanceof APIError ? err.message : "Failed to reset chat";
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [profile?.phone]);

  // ─── Conversation History Actions ──────────────────────────────────────

  const loadConversations = useCallback(async (phone: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await candidateAPI.getConversations(phone);
      setConversations(result);
    } catch (err) {
      const message =
        err instanceof APIError ? err.message : "Failed to load conversations";
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadConversationMessages = useCallback(async (sessionId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await candidateAPI.getConversationMessages(sessionId);
      setMessages(result);
      setSessionId(sessionId);
    } catch (err) {
      const message =
        err instanceof APIError ? err.message : "Failed to load messages";
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  // ─── Feedback Actions ──────────────────────────────────────────────────

  const submitFeedback = useCallback(
    async (
      sessionId: string,
      turn: number,
      rating: "up" | "down",
      note?: string
    ) => {
      setError(null);
      try {
        await candidateAPI.submitFeedback({
          session_id: sessionId,
          turn_number: turn,
          rating,
          note,
        });

        // Update local message state
        setMessages((prev) =>
          prev.map((msg) =>
            msg.turn === turn ? { ...msg, feedback: rating } : msg
          )
        );
      } catch (err) {
        const message =
          err instanceof APIError ? err.message : "Failed to submit feedback";
        setError(message);
        throw err;
      }
    },
    []
  );

  // ─── Utility Actions ────────────────────────────────────────────────────

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const logout = useCallback(() => {
    setProfile(null);
    setSessionId(null);
    setMessages([]);
    setConversations(null);
    setError(null);
    if (typeof window !== "undefined") {
      localStorage.removeItem("zia_phone");
      localStorage.removeItem("zia_session");
    }
  }, []);

  // ─── Context Value ────────────────────────────────────────────────────

  const value: AppContextType = {
    profile,
    sessionId,
    messages,
    isLoading,
    error,
    isSendingMessage,
    conversations,
    createOrGetProfile,
    getProfile,
    updateProfile,
    sendMessage,
    resetChat,
    loadConversations,
    loadConversationMessages,
    submitFeedback,
    clearError,
    logout,
  };

  return (
    <ChatContext.Provider value={value}>
      {children}
    </ChatContext.Provider>
  );
}

// ─── Hook: useChat ────────────────────────────────────────────────────────

export function useChat(): AppContextType {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error("useChat must be used within a ChatProvider");
  }
  return context;
}
