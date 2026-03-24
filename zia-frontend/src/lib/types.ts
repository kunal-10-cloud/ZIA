/**
 * Zia Frontend — TypeScript Types
 * ================================
 * All API request/response types and internal state shapes.
 */

// ─── Candidate Profile ─────────────────────────────────────────────────────

export interface CompanionProfile {
  id: string;
  phone: string;
  name: string | null;
  gender: string;
  current_role: string | null;
  yoe: number | null;
  tech_stack: string | null;
  company: string | null;
  company_type: string | null;
  location: string | null;
  comp_current: number | null;
  comp_target: number | null;
  goals: string | null;
  relationship_stage: number;
  mixing_board_state: {
    priyanka: number;
    sister: number;
  };
  assessment_status: string;
  nudge_count: number;
}

export interface CreateProfileRequest {
  phone: string;
  name: string;
}

export interface UpdateProfileRequest {
  phone: string;
  name?: string | null;
  current_role?: string | null;
  yoe?: number | null;
  tech_stack?: string | null;
  company?: string | null;
  company_type?: string | null;
  location?: string | null;
  comp_current?: number | null;
  comp_target?: number | null;
  goals?: string | null;
}

// ─── Conversation & Messages ──────────────────────────────────────────────

export interface MessageRecord {
  turn: number;
  user_message: string;
  zia_response: string;
  active_skill: string;
  timestamp: string;
  feedback: "up" | "down" | null;
}

export interface ConversationRecord {
  id: string;
  candidate_id: string;
  channel: string;
  started_at: string;
  ended_at: string | null;
  turn_count: number;
  relationship_stage_at_start: number;
  messages: MessageRecord[];
  created_at: string;
}

// ─── Chat API ─────────────────────────────────────────────────────────────

export interface ChatRequest {
  message: string;
  session_id?: string;
  phone?: string;
}

export interface ChatResponse {
  response: string;
  session_id: string;
  active_skill: string;
  routing_method?: string;
  token_count?: number;
  overrides?: string[];
  turn_number: number;
  timestamp: string;
  voss_activated?: boolean;
  blocked_nudge?: boolean;
}

export interface ChatResetResponse {
  message: string;
  cleared_turns: number;
}

// ─── Feedback ────────────────────────────────────────────────────────────

export interface SubmitFeedbackRequest {
  session_id: string;
  turn_number: number;
  rating: "up" | "down";
  note?: string | null;
}

export interface SubmitFeedbackResponse {
  success: boolean;
  message: string;
}

// ─── UI State ────────────────────────────────────────────────────────────

export interface ChatState {
  profile: CompanionProfile | null;
  sessionId: string | null;
  messages: MessageRecord[];
  isLoading: boolean;
  error: string | null;
  isSendingMessage: boolean;
}

export interface AppContextType {
  // State
  profile: CompanionProfile | null;
  sessionId: string | null;
  messages: MessageRecord[];
  isLoading: boolean;
  error: string | null;
  isSendingMessage: boolean;
  conversations: ConversationRecord[] | null;

  // Actions
  createOrGetProfile: (phone: string, name: string) => Promise<void>;
  getProfile: (phone: string) => Promise<void>;
  updateProfile: (data: UpdateProfileRequest) => Promise<void>;
  sendMessage: (message: string) => Promise<void>;
  resetChat: () => Promise<void>;
  loadConversations: (phone: string) => Promise<void>;
  loadConversationMessages: (sessionId: string) => Promise<void>;
  submitFeedback: (sessionId: string, turn: number, rating: "up" | "down", note?: string) => Promise<void>;
  clearError: () => void;
  logout: () => void;
}
