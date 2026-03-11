"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useRef,
  useCallback,
  ReactNode,
} from "react";
import { useAuth } from "@/lib/auth-context";
import { WebRTCManager } from "@/lib/webrtc";

/* ─── Types ─── */

export type CallState = "idle" | "outgoing" | "ringing" | "active";

export interface CallInfo {
  callId: number | null;
  peerId: number;
  peerName: string;
  jobId?: number | null;
  startTime?: number; // timestamp when call became active
}

interface CallContextType {
  callState: CallState;
  callInfo: CallInfo | null;
  isMuted: boolean;
  elapsed: number; // seconds since call became active
  startCall: (userId: number, userName: string, jobId?: number) => Promise<void>;
  acceptCall: () => Promise<void>;
  rejectCall: () => void;
  endCall: () => void;
  toggleMute: () => void;
  isConnected: boolean; // WebSocket connection status
}

const CallContext = createContext<CallContextType | undefined>(undefined);

const RAILWAY_BACKEND = "https://bridge-point-production.up.railway.app";

// In production, WebSocket must connect directly to Railway (Vercel proxy doesn't support WS).
// Locally, connect to the dev backend.
const isProduction = typeof window !== "undefined" && !window.location.hostname.includes("localhost");
const API_BASE = isProduction
  ? RAILWAY_BACKEND
  : (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000");
const WS_BASE = API_BASE.replace(/^http/, "ws");

export function CallProvider({ children }: { children: ReactNode }) {
  const { token, user } = useAuth();

  // ─── State ───
  const [callState, setCallState] = useState<CallState>("idle");
  const [callInfo, setCallInfo] = useState<CallInfo | null>(null);
  const [isMuted, setIsMuted] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [isConnected, setIsConnected] = useState(false);

  // ─── Refs ───
  const wsRef = useRef<WebSocket | null>(null);
  const rtcRef = useRef<WebRTCManager | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pendingOfferRef = useRef<RTCSessionDescriptionInit | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isReconnectingRef = useRef(false);
  const callStateRef = useRef<CallState>("idle");
  const callInfoRef = useRef<CallInfo | null>(null);

  // Keep refs in sync for access inside callbacks
  useEffect(() => {
    callStateRef.current = callState;
  }, [callState]);
  useEffect(() => {
    callInfoRef.current = callInfo;
  }, [callInfo]);

  // ─── Audio Element ───
  useEffect(() => {
    if (typeof window !== "undefined" && !audioRef.current) {
      audioRef.current = new Audio();
      audioRef.current.autoplay = true;
    }
  }, []);

  // ─── Timer ───
  useEffect(() => {
    if (callState === "active" && callInfo?.startTime) {
      timerRef.current = setInterval(() => {
        setElapsed(Math.floor((Date.now() - callInfo.startTime!) / 1000));
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
      if (callState === "idle") setElapsed(0);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [callState, callInfo?.startTime]);

  // ─── Cleanup function ───
  const cleanupCall = useCallback(() => {
    if (rtcRef.current) {
      rtcRef.current.cleanup();
      rtcRef.current = null;
    }
    if (audioRef.current) {
      audioRef.current.srcObject = null;
    }
    pendingOfferRef.current = null;
    setCallState("idle");
    setCallInfo(null);
    setIsMuted(false);
    setElapsed(0);
    if (timerRef.current) clearInterval(timerRef.current);
  }, []);

  // ─── Send message via WebSocket ───
  const wsSend = useCallback((msg: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }, []);

  // ─── Create WebRTC manager ───
  const createRTC = useCallback(() => {
    const manager = new WebRTCManager({
      onRemoteStream: (stream) => {
        if (audioRef.current) {
          audioRef.current.srcObject = stream;
          audioRef.current.play().catch(() => {});
        }
      },
      onICECandidate: (candidate) => {
        const info = callInfoRef.current;
        if (info) {
          wsSend({
            type: "call:ice",
            to_user_id: info.peerId,
            call_id: info.callId,
            candidate,
          });
        }
      },
      onConnectionStateChange: (state) => {
        if (state === "failed" || state === "disconnected") {
          // Connection lost — end the call
          const info = callInfoRef.current;
          if (info?.callId) {
            wsSend({ type: "call:end", call_id: info.callId });
          }
          cleanupCall();
        }
      },
    });
    rtcRef.current = manager;
    return manager;
  }, [wsSend, cleanupCall]);

  // ─── WebSocket Message Handler ───
  const handleWSMessage = useCallback(
    async (event: MessageEvent) => {
      if (event.data === "pong") return;

      let msg: Record<string, unknown>;
      try {
        msg = JSON.parse(event.data as string);
      } catch {
        return;
      }

      const type = msg.type as string;

      switch (type) {
        // ─── Incoming call offer ───
        case "call:offer": {
          // If already in a call, send busy
          if (callStateRef.current !== "idle") {
            wsSend({
              type: "call:busy",
              to_user_id: msg.from_user_id,
              call_id: msg.call_id,
            });
            return;
          }

          // Store the offer and show incoming call UI
          pendingOfferRef.current = msg.sdp as RTCSessionDescriptionInit;
          setCallState("ringing");
          setCallInfo({
            callId: msg.call_id as number,
            peerId: msg.from_user_id as number,
            peerName: (msg.caller_name as string) || "Unknown",
            jobId: msg.job_id as number | null,
          });
          break;
        }

        // ─── Call confirmed ringing ───
        case "call:ringing": {
          setCallInfo((prev) =>
            prev ? { ...prev, callId: msg.call_id as number } : prev
          );
          break;
        }

        // ─── Call answer received ───
        case "call:answer": {
          if (rtcRef.current) {
            await rtcRef.current.setRemoteAnswer(
              msg.sdp as RTCSessionDescriptionInit
            );
            setCallState("active");
            setCallInfo((prev) =>
              prev ? { ...prev, startTime: Date.now() } : prev
            );
          }
          break;
        }

        // ─── ICE candidate ───
        case "call:ice": {
          if (rtcRef.current && msg.candidate) {
            await rtcRef.current.addICECandidate(
              msg.candidate as RTCIceCandidateInit
            );
          }
          break;
        }

        // ─── Call rejected by callee ───
        case "call:rejected": {
          cleanupCall();
          break;
        }

        // ─── Call ended by peer ───
        case "call:ended":
        case "call:end": {
          cleanupCall();
          break;
        }

        // ─── Callee is offline ───
        case "call:user_offline": {
          cleanupCall();
          break;
        }

        // ─── Callee is busy ───
        case "call:busy": {
          cleanupCall();
          break;
        }
      }
    },
    [wsSend, cleanupCall]
  );

  // ─── WebSocket Connection ───
  useEffect(() => {
    if (!token || !user) {
      // Disconnect if logged out
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
        setIsConnected(false);
      }
      return;
    }

    const connect = () => {
      const ws = new WebSocket(`${WS_BASE}/ws/${token}`);

      ws.onopen = () => {
        setIsConnected(true);
        isReconnectingRef.current = false;
        // Start keepalive pings every 25 seconds
        const pingInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send("ping");
          }
        }, 25_000);
        (ws as unknown as Record<string, unknown>)._pingInterval = pingInterval;
      };

      ws.onmessage = handleWSMessage;

      ws.onclose = () => {
        setIsConnected(false);
        const interval = (ws as unknown as Record<string, unknown>)
          ._pingInterval as ReturnType<typeof setInterval>;
        if (interval) clearInterval(interval);

        // Auto-reconnect after 3 seconds (with guard against stacking)
        if (!isReconnectingRef.current) {
          isReconnectingRef.current = true;
          reconnectTimeoutRef.current = setTimeout(() => {
            if (token && user) connect();
          }, 3_000);
        }
      };

      ws.onerror = () => {
        ws.close();
      };

      wsRef.current = ws;
    };

    connect();

    return () => {
      if (reconnectTimeoutRef.current)
        clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) {
        const interval = (wsRef.current as unknown as Record<string, unknown>)
          ._pingInterval as ReturnType<typeof setInterval>;
        if (interval) clearInterval(interval);
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [token, user, handleWSMessage]);

  // ─── Public Actions ───

  const startCall = useCallback(
    async (userId: number, userName: string, jobId?: number) => {
      if (callStateRef.current !== "idle") return;

      setCallState("outgoing");
      setCallInfo({
        callId: null,
        peerId: userId,
        peerName: userName,
        jobId: jobId || null,
      });

      try {
        const rtc = createRTC();
        await rtc.initialize();
        const offer = await rtc.createOffer();

        wsSend({
          type: "call:offer",
          to_user_id: userId,
          job_id: jobId || null,
          caller_name: user?.full_name || "Unknown",
          sdp: offer,
        });
      } catch (err) {
        console.error("Failed to start call:", err);
        cleanupCall();
      }
    },
    [createRTC, wsSend, cleanupCall, user?.full_name]
  );

  const acceptCall = useCallback(async () => {
    if (callStateRef.current !== "ringing" || !pendingOfferRef.current) return;

    try {
      const rtc = createRTC();
      await rtc.initialize();
      const answer = await rtc.createAnswer(pendingOfferRef.current);

      const info = callInfoRef.current;
      wsSend({
        type: "call:answer",
        to_user_id: info?.peerId,
        call_id: info?.callId,
        sdp: answer,
      });

      setCallState("active");
      setCallInfo((prev) =>
        prev ? { ...prev, startTime: Date.now() } : prev
      );
      pendingOfferRef.current = null;
    } catch (err) {
      console.error("Failed to accept call:", err);
      cleanupCall();
    }
  }, [createRTC, wsSend, cleanupCall]);

  const rejectCall = useCallback(() => {
    const info = callInfoRef.current;
    if (info) {
      wsSend({
        type: "call:reject",
        to_user_id: info.peerId,
        call_id: info.callId,
      });
    }
    cleanupCall();
  }, [wsSend, cleanupCall]);

  const endCall = useCallback(() => {
    const info = callInfoRef.current;
    if (info?.callId) {
      wsSend({
        type: "call:end",
        call_id: info.callId,
      });
    }
    cleanupCall();
  }, [wsSend, cleanupCall]);

  const toggleMute = useCallback(() => {
    if (rtcRef.current) {
      const muted = rtcRef.current.toggleMute();
      setIsMuted(muted);
    }
  }, []);

  return (
    <CallContext.Provider
      value={{
        callState,
        callInfo,
        isMuted,
        elapsed,
        startCall,
        acceptCall,
        rejectCall,
        endCall,
        toggleMute,
        isConnected,
      }}
    >
      {children}
    </CallContext.Provider>
  );
}

export function useCall() {
  const ctx = useContext(CallContext);
  if (!ctx) throw new Error("useCall must be inside CallProvider");
  return ctx;
}
