/**
 * Zia Frontend — API Client
 * =========================
 * Axios wrapper for all backend API calls.
 */

import axios, { AxiosInstance } from "axios";
import {
  CompanionProfile,
  CreateProfileRequest,
  UpdateProfileRequest,
  ChatRequest,
  ChatResponse,
  ChatResetResponse,
  ConversationRecord,
  SubmitFeedbackRequest,
  SubmitFeedbackResponse,
  MessageRecord,
} from "./types";

// ─── Config ────────────────────────────────────────────────────────────────
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ─── Axios Instance ────────────────────────────────────────────────────────
const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// ─── Candidate Profile Endpoints ───────────────────────────────────────────

export const candidateAPI = {
  /**
   * Create or get profile by phone number.
   * If profile exists, returns existing. Otherwise creates new.
   */
  createOrGetProfile: async (
    data: CreateProfileRequest
  ): Promise<CompanionProfile> => {
    const response = await api.post<CompanionProfile>(
      "/candidate/profile/create-or-get",
      data
    );
    return response.data;
  },

  /**
   * Get profile by phone number.
   */
  getProfile: async (phone: string): Promise<CompanionProfile> => {
    const response = await api.get<CompanionProfile>(
      `/candidate/profile/${encodeURIComponent(phone)}`
    );
    return response.data;
  },

  /**
   * Update profile fields.
   */
  updateProfile: async (
    data: UpdateProfileRequest
  ): Promise<CompanionProfile> => {
    const response = await api.post<CompanionProfile>(
      "/candidate/profile/update",
      data
    );
    return response.data;
  },

  /**
   * Get all conversations for a candidate (by phone).
   */
  getConversations: async (phone: string): Promise<ConversationRecord[]> => {
    const response = await api.get<ConversationRecord[]>(
      `/candidate/conversations/${encodeURIComponent(phone)}`
    );
    return response.data;
  },

  /**
   * Get messages from a specific conversation session.
   */
  getConversationMessages: async (sessionId: string): Promise<MessageRecord[]> => {
    const response = await api.get<MessageRecord[]>(
      `/candidate/conversation/${encodeURIComponent(sessionId)}/messages`
    );
    return response.data;
  },

  /**
   * Submit feedback (👍/👎) for a specific message.
   */
  submitFeedback: async (
    data: SubmitFeedbackRequest
  ): Promise<SubmitFeedbackResponse> => {
    const response = await api.post<SubmitFeedbackResponse>(
      "/candidate/feedback",
      data
    );
    return response.data;
  },
};

// ─── Chat Endpoints ────────────────────────────────────────────────────────

export const chatAPI = {
  /**
   * Send a message to Zia and get response.
   * Creates new session if session_id not provided.
   */
  sendMessage: async (data: ChatRequest): Promise<ChatResponse> => {
    const response = await api.post<ChatResponse>("/chat", data);
    return response.data;
  },

  /**
   * Reset the current chat session.
   */
  reset: async (): Promise<ChatResetResponse> => {
    const response = await api.post<ChatResetResponse>("/chat/reset");
    return response.data;
  },

  /**
   * Health check endpoint.
   */
  health: async (): Promise<{ status: string; phase: string }> => {
    const response = await api.get<{ status: string; phase: string }>("/health");
    return response.data;
  },
};

// ─── Error Handling ────────────────────────────────────────────────────────

export class APIError extends Error {
  constructor(
    public status: number,
    public message: string,
    public data?: unknown
  ) {
    super(message);
    this.name = "APIError";
  }
}

// ─── Axios Interceptor for Error Handling ────────────────────────────────

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error) && error.response) {
      // FastAPI returns errors with 'detail' field
      const message = error.response.data?.detail || error.response.data?.message || error.message;
      throw new APIError(
        error.response.status,
        message,
        error.response.data
      );
    }
    throw error;
  }
);

export default api;
