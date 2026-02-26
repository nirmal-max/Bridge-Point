"use client";

import { useEffect, useState, useRef } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

interface ChatMessage {
  id: number;
  job_id: number;
  sender_id: number;
  sender_name: string | null;
  content: string;
  created_at: string;
}

interface ChatPanelProps {
  jobId: number;
  isParticipant: boolean;
}

export default function ChatPanel({ jobId, isParticipant }: ChatPanelProps) {
  const { user } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [newMessage, setNewMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isParticipant) return;
    const fetchMessages = async () => {
      try {
        const msgs = await api.getJobMessages(jobId);
        setMessages(msgs);
      } catch {
        /* silently fail */
      } finally {
        setLoading(false);
      }
    };
    fetchMessages();
    // Poll every 5s for new messages (supplement to WebSocket)
    const interval = setInterval(fetchMessages, 5000);
    return () => clearInterval(interval);
  }, [jobId, isParticipant]);

  useEffect(() => {
    // Auto-scroll to bottom on new messages
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim() || sending) return;

    setSending(true);
    try {
      const msg = await api.sendMessage(jobId, newMessage.trim());
      setMessages((prev) => [...prev, msg]);
      setNewMessage("");
    } catch {
      /* */
    } finally {
      setSending(false);
    }
  };

  if (!isParticipant) return null;

  return (
    <div className="card !p-0 overflow-hidden">
      <div className="px-5 py-3 border-b border-[var(--color-bp-gray-200)] bg-[var(--color-bp-gray-100)]">
        <h3 className="text-sm font-semibold text-[var(--color-bp-gray-600)] uppercase tracking-wider">
          💬 Chat
        </h3>
      </div>

      {/* Messages Area */}
      <div
        ref={scrollRef}
        className="h-64 overflow-y-auto px-5 py-3 space-y-3"
      >
        {loading ? (
          <div className="text-center text-sm text-[var(--color-bp-gray-400)] py-8">
            Loading messages...
          </div>
        ) : messages.length === 0 ? (
          <div className="text-center text-sm text-[var(--color-bp-gray-400)] py-8">
            No messages yet. Say hello!
          </div>
        ) : (
          messages.map((msg) => {
            const isMine = msg.sender_id === user?.id;
            return (
              <div
                key={msg.id}
                className={`flex ${isMine ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[75%] rounded-2xl px-4 py-2.5 ${
                    isMine
                      ? "bg-[var(--color-bp-blue)] text-white rounded-br-md"
                      : "bg-[var(--color-bp-gray-100)] text-[var(--color-bp-black)] rounded-bl-md"
                  }`}
                >
                  {!isMine && (
                    <div className="text-[10px] font-semibold text-[var(--color-bp-gray-500)] mb-0.5">
                      {msg.sender_name || "Unknown"}
                    </div>
                  )}
                  <div className="text-sm leading-relaxed">{msg.content}</div>
                  <div
                    className={`text-[10px] mt-1 ${
                      isMine ? "text-blue-100" : "text-[var(--color-bp-gray-400)]"
                    }`}
                  >
                    {new Date(msg.created_at).toLocaleTimeString("en-IN", {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Input */}
      <form
        onSubmit={handleSend}
        className="flex items-center gap-2 px-4 py-3 border-t border-[var(--color-bp-gray-200)]"
      >
        <input
          type="text"
          className="input-field !mb-0 flex-1"
          placeholder="Type a message..."
          value={newMessage}
          onChange={(e) => setNewMessage(e.target.value)}
          maxLength={2000}
        />
        <button
          type="submit"
          disabled={sending || !newMessage.trim()}
          className="btn-primary !py-3 !px-5 disabled:opacity-50"
        >
          {sending ? "..." : "Send"}
        </button>
      </form>
    </div>
  );
}
