"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Step = "email" | "otp" | "reset" | "done";

export default function ForgotPasswordPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("email");
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const handleRequestOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Request failed");
      setMessage(data.message);
      setStep("otp");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to send OTP");
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/auth/verify-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, otp }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Verification failed");
      setResetToken(data.reset_token);
      setMessage("");
      setStep("reset");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "OTP verification failed");
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (newPassword.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/auth/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reset_token: resetToken, new_password: newPassword }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Reset failed");
      setStep("done");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Password reset failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="pt-14 min-h-screen bg-[var(--color-bp-gray-100)] flex items-center justify-center">
      <div className="max-w-md w-full mx-auto px-6">
        <div className="text-center mb-10">
          <h1 className="text-3xl font-semibold tracking-tight text-[var(--color-bp-black)]">
            {step === "done" ? "Password Reset!" : "Forgot Password"}
          </h1>
          <p className="text-[var(--color-bp-gray-500)] mt-3">
            {step === "email" && "Enter your email to receive a reset code."}
            {step === "otp" && "Enter the 6-digit code sent to your email."}
            {step === "reset" && "Set your new password."}
            {step === "done" && "Your password has been updated successfully."}
          </p>
        </div>

        {error && (
          <div className="p-4 rounded-xl bg-red-50 text-red-700 text-sm border border-red-200 mb-4">
            {error}
          </div>
        )}

        {message && step === "otp" && (
          <div className="p-4 rounded-xl bg-blue-50 text-blue-700 text-sm border border-blue-200 mb-4">
            {message}
          </div>
        )}

        {/* Step 1: Email Input */}
        {step === "email" && (
          <form onSubmit={handleRequestOtp} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-[var(--color-bp-gray-700)] mb-1.5">
                Email Address
              </label>
              <input
                type="email"
                className="input-field"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoFocus
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full !py-4 !text-base mt-2"
            >
              {loading ? "Sending..." : "Send Reset Code"}
            </button>
          </form>
        )}

        {/* Step 2: OTP Input */}
        {step === "otp" && (
          <form onSubmit={handleVerifyOtp} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-[var(--color-bp-gray-700)] mb-1.5">
                6-Digit Code
              </label>
              <input
                type="text"
                className="input-field text-center text-2xl tracking-[0.5em] font-mono"
                placeholder="000000"
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
                maxLength={6}
                required
                autoFocus
              />
            </div>
            <button
              type="submit"
              disabled={loading || otp.length !== 6}
              className="btn-primary w-full !py-4 !text-base mt-2"
            >
              {loading ? "Verifying..." : "Verify Code"}
            </button>
            <button
              type="button"
              onClick={() => { setStep("email"); setError(""); setOtp(""); }}
              className="btn-secondary w-full !py-3"
            >
              ← Back
            </button>
          </form>
        )}

        {/* Step 3: New Password */}
        {step === "reset" && (
          <form onSubmit={handleResetPassword} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-[var(--color-bp-gray-700)] mb-1.5">
                New Password
              </label>
              <input
                type="password"
                className="input-field"
                placeholder="Minimum 8 characters"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                autoFocus
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--color-bp-gray-700)] mb-1.5">
                Confirm Password
              </label>
              <input
                type="password"
                className="input-field"
                placeholder="Re-enter your new password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full !py-4 !text-base mt-2"
            >
              {loading ? "Resetting..." : "Reset Password"}
            </button>
          </form>
        )}

        {/* Step 4: Success */}
        {step === "done" && (
          <div className="text-center">
            <div className="text-5xl mb-4">✅</div>
            <button
              onClick={() => router.push("/login")}
              className="btn-primary w-full !py-4 !text-base mt-4"
            >
              Go to Login
            </button>
          </div>
        )}

        <p className="text-center text-sm text-[var(--color-bp-gray-500)] mt-6">
          Remember your password?{" "}
          <Link href="/login" className="text-[var(--color-bp-blue)] font-medium">
            Sign In
          </Link>
        </p>
      </div>
    </div>
  );
}
