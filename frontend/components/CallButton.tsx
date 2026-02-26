"use client";

import { useCall } from "@/lib/call-context";

interface CallButtonProps {
  userId: number;
  userName: string;
  jobId?: number;
  size?: "sm" | "md" | "lg";
  variant?: "icon" | "full";
  className?: string;
}

export default function CallButton({
  userId,
  userName,
  jobId,
  size = "md",
  variant = "icon",
  className = "",
}: CallButtonProps) {
  const { startCall, callState, isConnected } = useCall();

  const disabled = callState !== "idle" || !isConnected;

  const handleClick = async () => {
    if (disabled) return;
    await startCall(userId, userName, jobId);
  };

  const sizeClasses = {
    sm: "w-8 h-8",
    md: "w-10 h-10",
    lg: "w-12 h-12",
  };

  const iconSizes = {
    sm: 16,
    md: 20,
    lg: 24,
  };

  if (variant === "full") {
    return (
      <button
        id={`call-btn-${userId}`}
        className={`call-button-full ${disabled ? "call-button-disabled" : ""} ${className}`}
        onClick={handleClick}
        disabled={disabled}
        title={!isConnected ? "Connecting..." : disabled ? "Already in a call" : `Call ${userName}`}
      >
        <svg
          width={iconSizes[size]}
          height={iconSizes[size]}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
        </svg>
        <span>Call {userName.split(" ")[0]}</span>
      </button>
    );
  }

  return (
    <button
      id={`call-btn-${userId}`}
      className={`call-button-icon ${sizeClasses[size]} ${disabled ? "call-button-disabled" : ""} ${className}`}
      onClick={handleClick}
      disabled={disabled}
      title={!isConnected ? "Connecting..." : disabled ? "Already in a call" : `Call ${userName}`}
    >
      <svg
        width={iconSizes[size]}
        height={iconSizes[size]}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
      </svg>
    </button>
  );
}
