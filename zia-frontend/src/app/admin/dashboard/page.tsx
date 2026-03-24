'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import axios from 'axios';

interface MessageRecord {
  turn: number;
  user_message: string;
  zia_response: string;
  active_skill?: string;
  timestamp: string;
  feedback?: string;
}

interface ConversationSummary {
  id: string;
  candidate_phone?: string;
  candidate_name?: string;
  channel: string;
  started_at: string;
  turn_count: number;
  message_preview?: string;
}

interface ConversationDetail {
  id: string;
  candidate_id: string;
  candidate_phone?: string;
  candidate_name?: string;
  channel: string;
  started_at: string;
  ended_at?: string;
  turn_count: number;
  relationship_stage_at_start: number;
  messages: MessageRecord[];
  created_at: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function AdminDashboard() {
  const router = useRouter();
  const [isAuth, setIsAuth] = useState(false);
  const [loading, setLoading] = useState(true);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [selectedConversation, setSelectedConversation] = useState<ConversationDetail | null>(null);
  const [stats, setStats] = useState({
    totalConversations: 0,
    totalMessages: 0,
    helpfulFeedback: 0,
    unhelpfulFeedback: 0,
  });
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('zia_admin_token');
    if (!token) {
      router.push('/admin');
      return;
    }
    
    setIsAuth(true);
    fetchConversations();
  }, [router]);

  const fetchConversations = async () => {
    try {
      setError(null);
      
      const response = await axios.get(`${API_BASE_URL}/admin/conversations`);
      const data = response.data;
      
      setConversations(data);
      setLastUpdated(new Date());

      // Calculate stats
      let totalMessages = 0;
      let helpfulCount = 0;
      let unhelpfulCount = 0;

      // Fetch details for each conversation to count messages and feedback
      for (const conv of data) {
        totalMessages += conv.turn_count * 2; // Each turn has user + Zia message
        
        try {
          const detailResponse = await axios.get(`${API_BASE_URL}/admin/conversations/${conv.id}`);
          const detailData = detailResponse.data;
          
          detailData.messages?.forEach((msg: MessageRecord) => {
            if (msg.feedback === 'up') helpfulCount++;
            if (msg.feedback === 'down') unhelpfulCount++;
          });

          // If this is the currently selected conversation, update it
          if (selectedConversation?.id === conv.id) {
            setSelectedConversation(detailData);
          }
        } catch (err) {
          console.error(`Error fetching conversation detail for ${conv.id}:`, err);
        }
      }

      setStats({
        totalConversations: data.length,
        totalMessages,
        helpfulFeedback: helpfulCount,
        unhelpfulFeedback: unhelpfulCount,
      });

      // Load first conversation if available and no conversation is selected
      if (data.length > 0 && !selectedConversation) {
        loadConversationDetail(data[0].id);
      }

      if (loading) {
        setLoading(false);
      }
    } catch (err) {
      console.error('Failed to fetch conversations:', err);
      const message = axios.isAxiosError(err) 
        ? err.response?.data?.detail || err.message 
        : String(err);
      setError(`Failed to load conversations: ${message}`);
      if (loading) {
        setLoading(false);
      }
    }
  };

  const loadConversationDetail = async (conversationId: string) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/admin/conversations/${conversationId}`);
      console.log('Conversation detail response:', response.data);
      console.log('Messages:', response.data.messages);
      setSelectedConversation(response.data);
    } catch (err) {
      console.error('Error loading conversation:', err);
      const message = axios.isAxiosError(err) 
        ? err.response?.data?.detail || err.message 
        : String(err);
      setError(`Failed to load conversation: ${message}`);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('zia_admin_token');
    router.push('/admin');
  };

  if (!isAuth) {
    return null;
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-slate-900 text-lg">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <div className="sticky top-0 z-40 bg-white border-b border-slate-200">
        <div className="px-6 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">Admin Dashboard</h1>
            {lastUpdated && (
              <p className="text-xs text-slate-500 mt-1">
                Last updated: {lastUpdated.toLocaleTimeString()}
              </p>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={fetchConversations}
              className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg transition-colors text-sm font-medium"
            >
              Refresh
            </button>
            <button
              onClick={handleLogout}
              className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-900 rounded-lg transition-colors text-sm font-medium"
            >
              Logout
            </button>
          </div>
        </div>
      </div>

      <div className="px-6 py-8 w-full">
        {/* Error Message */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">
            {error}
          </div>
        )}

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div className="bg-white border border-slate-200 rounded-lg p-6">
            <div className="text-sm text-slate-500 mb-2">Conversations</div>
            <div className="text-3xl font-semibold text-slate-900">{stats.totalConversations}</div>
          </div>
          <div className="bg-white border border-slate-200 rounded-lg p-6">
            <div className="text-sm text-slate-500 mb-2">Messages</div>
            <div className="text-3xl font-semibold text-slate-900">{stats.totalMessages}</div>
          </div>
          <div className="bg-white border border-slate-200 rounded-lg p-6">
            <div className="text-sm text-slate-500 mb-2">Helpful</div>
            <div className="text-3xl font-semibold text-green-600">{stats.helpfulFeedback}</div>
          </div>
          <div className="bg-white border border-slate-200 rounded-lg p-6">
            <div className="text-sm text-slate-500 mb-2">Unhelpful</div>
            <div className="text-3xl font-semibold text-red-600">{stats.unhelpfulFeedback}</div>
          </div>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Conversations Sidebar */}
          <div className="lg:col-span-1 bg-white border border-slate-200 rounded-lg overflow-hidden flex flex-col h-[600px]">
            <div className="bg-slate-50 px-4 py-3 border-b border-slate-200">
              <h2 className="text-slate-900 font-semibold text-sm">Conversations ({conversations.length})</h2>
            </div>
            <div className="overflow-y-auto flex-1">
              {conversations.length === 0 ? (
                <div className="text-slate-500 text-sm p-4">No conversations yet</div>
              ) : (
                conversations.map((conv) => (
                  <div
                    key={conv.id}
                    onClick={() => loadConversationDetail(conv.id)}
                    className={`p-3 border-b border-slate-100 cursor-pointer transition-colors text-sm ${
                      selectedConversation?.id === conv.id
                        ? 'bg-blue-50 border-l-2 border-l-blue-600'
                        : 'hover:bg-slate-50'
                    }`}
                  >
                    <div className="text-slate-900 font-medium truncate text-sm">
                      {conv.candidate_name || conv.candidate_phone || 'Unknown'}
                    </div>
                    <div className="text-slate-500 text-xs mt-1 truncate">
                      {conv.message_preview || 'No messages'}
                    </div>
                    <div className="text-slate-400 text-xs mt-1">
                      {conv.turn_count} turns • {new Date(conv.started_at).toLocaleDateString()}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Conversation Detail */}
          <div className="lg:col-span-2 bg-white border border-slate-200 rounded-lg overflow-hidden h-[600px] flex flex-col">
            {selectedConversation ? (
              <>
                <div className="bg-slate-50 px-4 py-3 border-b border-slate-200">
                  <h2 className="text-slate-900 font-semibold">
                    {selectedConversation.candidate_name || selectedConversation.candidate_phone || 'Unknown'}
                  </h2>
                  <p className="text-slate-500 text-xs mt-1">
                    {selectedConversation.turn_count} turns • {new Date(selectedConversation.started_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                  {selectedConversation.messages && selectedConversation.messages.length > 0 ? (
                    selectedConversation.messages.map((msg, idx) => (
                      <div key={idx} className="space-y-2">
                        {/* User Message */}
                        <div className="flex justify-end">
                          <div className="bg-slate-900 text-white rounded-lg p-3 max-w-xs lg:max-w-sm text-sm">
                            {msg.user_message}
                          </div>
                        </div>
                        {/* Zia Response */}
                        <div className="flex justify-start">
                          <div className="bg-slate-100 text-slate-900 rounded-lg p-3 max-w-xs lg:max-w-sm text-sm">
                            {msg.zia_response}
                          </div>
                        </div>
                        {/* Feedback */}
                        {msg.feedback && (
                          <div className="flex justify-start pl-2">
                            <span className={`text-xs font-medium ${
                              msg.feedback === 'up' ? 'text-green-600' : 'text-red-600'
                            }`}>
                              {msg.feedback === 'up' ? 'Helpful' : 'Not helpful'}
                            </span>
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <div className="text-slate-400 text-sm">No messages</div>
                  )}
                </div>
              </>
            ) : (
              <div className="flex items-center justify-center h-full text-slate-400">
                Select a conversation to view details
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
