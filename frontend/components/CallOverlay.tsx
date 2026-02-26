"use client";

import { useCall } from "@/lib/call-context";

/* ─── Helper: format seconds to MM:SS ─── */
function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
    .toString()
    .padStart(2, "0");
  const s = (seconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

export default function CallOverlay() {
  const {
    callState,
    callInfo,
    isMuted,
    elapsed,
    acceptCall,
    rejectCall,
    endCall,
    toggleMute,
  } = useCall();

  if (callState === "idle" || !callInfo) return null;

  return (
    <div className="call-overlay" id="call-overlay">
      <div className="call-overlay-backdrop" />

      <div className="call-overlay-content">
        {/* ─── Avatar ─── */}
        <div className="call-avatar">
          <div className="call-avatar-circle">
            <span className="call-avatar-letter">
              {callInfo.peerName.charAt(0).toUpperCase()}
            </span>
            {(callState === "outgoing" || callState === "ringing") && (
              <>
                <div className="call-pulse-ring call-pulse-ring-1" />
                <div className="call-pulse-ring call-pulse-ring-2" />
                <div className="call-pulse-ring call-pulse-ring-3" />
              </>
            )}
          </div>
        </div>

        {/* ─── Info ─── */}
        <h2 className="call-peer-name">{callInfo.peerName}</h2>

        <p className="call-status-label">
          {callState === "outgoing" && "Calling..."}
          {callState === "ringing" && "Incoming Call"}
          {callState === "active" && formatTime(elapsed)}
        </p>

        {callInfo.jobId && (
          <p className="call-job-tag">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 7h-4V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v3H4a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2zM10 4h4v3h-4z" />
            </svg>
            Job #{callInfo.jobId}
          </p>
        )}

        {/* ─── Active Call Controls ─── */}
        {callState === "active" && (
          <div className="call-waveform">
            <div className="call-waveform-bar" style={{ animationDelay: "0ms" }} />
            <div className="call-waveform-bar" style={{ animationDelay: "150ms" }} />
            <div className="call-waveform-bar" style={{ animationDelay: "300ms" }} />
            <div className="call-waveform-bar" style={{ animationDelay: "450ms" }} />
            <div className="call-waveform-bar" style={{ animationDelay: "200ms" }} />
          </div>
        )}

        {/* ─── Action Buttons ─── */}
        <div className="call-actions">
          {/* Incoming call: Accept + Decline */}
          {callState === "ringing" && (
            <>
              <button
                id="call-decline-btn"
                className="call-action-btn call-action-decline"
                onClick={rejectCall}
                aria-label="Decline call"
              >
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M10.68 13.31a16 16 0 0 0 3.41 2.6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7 2 2 0 0 1 1.72 2v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91" />
                  <line x1="1" y1="1" x2="23" y2="23" />
                </svg>
                <span className="call-action-label">Decline</span>
              </button>

              <button
                id="call-accept-btn"
                className="call-action-btn call-action-accept"
                onClick={acceptCall}
                aria-label="Accept call"
              >
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
                </svg>
                <span className="call-action-label">Accept</span>
              </button>
            </>
          )}

          {/* Outgoing call: Cancel */}
          {callState === "outgoing" && (
            <button
              id="call-cancel-btn"
              className="call-action-btn call-action-decline"
              onClick={endCall}
              aria-label="Cancel call"
            >
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M10.68 13.31a16 16 0 0 0 3.41 2.6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7 2 2 0 0 1 1.72 2v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91" />
                <line x1="1" y1="1" x2="23" y2="23" />
              </svg>
              <span className="call-action-label">Cancel</span>
            </button>
          )}

          {/* Active call: Mute + End */}
          {callState === "active" && (
            <>
              <button
                id="call-mute-btn"
                className={`call-action-btn ${isMuted ? "call-action-muted" : "call-action-mute"}`}
                onClick={toggleMute}
                aria-label={isMuted ? "Unmute" : "Mute"}
              >
                {isMuted ? (
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="1" y1="1" x2="23" y2="23" />
                    <path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6" />
                    <path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2c0 .76-.13 1.49-.35 2.17" />
                    <line x1="12" y1="19" x2="12" y2="23" />
                    <line x1="8" y1="23" x2="16" y2="23" />
                  </svg>
                ) : (
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                    <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                    <line x1="12" y1="19" x2="12" y2="23" />
                    <line x1="8" y1="23" x2="16" y2="23" />
                  </svg>
                )}
                <span className="call-action-label">{isMuted ? "Unmute" : "Mute"}</span>
              </button>

              <button
                id="call-end-btn"
                className="call-action-btn call-action-decline"
                onClick={endCall}
                aria-label="End call"
              >
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M10.68 13.31a16 16 0 0 0 3.41 2.6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7 2 2 0 0 1 1.72 2v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91" />
                  <line x1="1" y1="1" x2="23" y2="23" />
                </svg>
                <span className="call-action-label">End Call</span>
              </button>
            </>
          )}
        </div>

        {/* ─── Connection indicator ─── */}
        {callState === "active" && (
          <div className="call-connection-info">
            <div className="call-connection-dot" />
            <span>Connected · Peer-to-peer encrypted</span>
          </div>
        )}
      </div>
    </div>
  );
}
