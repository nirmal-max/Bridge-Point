"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import {
  Job,
  STATUS_LABELS,
  STATUS_COLORS,
  WORK_DESCRIPTIONS,
} from "@/lib/types";
import CallButton from "@/components/CallButton";
import ProgressBar from "@/components/ProgressBar";
import ChatPanel from "@/components/ChatPanel";

// Who can trigger each work stage transition
const NEXT_STATUS: Record<string, { target: string; allowedRole: "labor" | "employer" | "both" }> = {
  labour_allotted: { target: "work_started", allowedRole: "labor" },
  work_started: { target: "work_in_progress", allowedRole: "labor" },
  work_in_progress: { target: "work_completed", allowedRole: "employer" },
};

// Statuses during which calling is allowed between employer and assigned labor
const CALL_ENABLED_STATUSES = ["labour_allotted", "work_started", "work_in_progress"];

export default function JobDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const router = useRouter();
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const [paymentMethod, setPaymentMethod] = useState<"upi" | "cash">("upi");
  const [upiRef, setUpiRef] = useState("");

  const jobId = Number(id);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const j = await api.getJob(jobId);
        setJob(j);
      } catch {
        setError("Job not found");
      } finally {
        setLoading(false);
      }
    };
    if (jobId) fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  // Auto-dismiss toast
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(""), 4000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  const wdLabel = (val: string) =>
    WORK_DESCRIPTIONS.find((w) => w.value === val)?.label || val;

  /* ─── Accept Task (instant first-come-first-serve) ─── */
  const handleAcceptTask = async () => {
    setActionLoading(true);
    setError("");
    try {
      await api.acceptTask(jobId);
      // Redirect to task-connected page on success
      router.push(`/task-connected/${jobId}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to accept task";
      if (msg.includes("already accepted")) {
        setToast("Task already accepted.");
        // Refresh job to show updated status
        try {
          const j = await api.getJob(jobId);
          setJob(j);
        } catch { /* */ }
      } else {
        setError(msg);
      }
    } finally {
      setActionLoading(false);
    }
  };

  const handleTransition = async (targetStatus: string) => {
    setActionLoading(true);
    try {
      const j = await api.updateJobStatus(jobId, targetStatus);
      setJob(j);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Transition failed");
    } finally {
      setActionLoading(false);
    }
  };

  const handlePayment = async () => {
    setActionLoading(true);
    try {
      await api.initiatePayment(jobId, paymentMethod);
      const j = await api.getJob(jobId);
      setJob(j);
      setToast("Payment initiated! Scan the QR code to pay.");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Payment initiation failed");
    } finally {
      setActionLoading(false);
    }
  };

  const handleMarkSent = async () => {
    setActionLoading(true);
    try {
      await api.markPaymentSent(jobId, upiRef);
      const j = await api.getJob(jobId);
      setJob(j);
      setToast("Payment marked as sent. Awaiting verification.");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to mark payment sent");
    } finally {
      setActionLoading(false);
    }
  };

  const handleAdminVerify = async () => {
    setActionLoading(true);
    try {
      await api.adminVerifyPayment(jobId);
      const j = await api.getJob(jobId);
      setJob(j);
      setToast("Payment verified!");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Verification failed");
    } finally {
      setActionLoading(false);
    }
  };

  const handleAdminRelease = async () => {
    setActionLoading(true);
    try {
      await api.adminReleasePayout(jobId);
      const j = await api.getJob(jobId);
      setJob(j);
      setToast("Payout released! Job complete.");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Payout release failed");
    } finally {
      setActionLoading(false);
    }
  };

  const handleAddFavorite = async () => {
    if (!job?.allotted_labor_id) return;
    try {
      await api.addFavorite(job.allotted_labor_id);
      setToast("Added to favorites!");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to add favorite");
    }
  };

  if (loading) {
    return (
      <div className="pt-14 min-h-screen bg-[var(--color-bp-gray-100)] flex items-center justify-center">
        <div className="text-[var(--color-bp-gray-500)]">Loading...</div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="pt-14 min-h-screen bg-[var(--color-bp-gray-100)] flex items-center justify-center">
        <div className="text-center">
          <div className="text-5xl mb-4">🔍</div>
          <h2 className="text-2xl font-semibold text-[var(--color-bp-black)]">Job not found</h2>
        </div>
      </div>
    );
  }

  const isOwner = user?.id === job.employer_id;
  const isAllottedLabor = user?.id === job.allotted_labor_id;
  
  // Only show "Accept Task" if:
  // 1. User is logged in
  // 2. User is NOT the owner
  // 3. User is NOT already the assigned labor
  // 4. Job is in 'posted' status
  const canAccept = user && !isOwner && !isAllottedLabor && job.status === "posted";
  const nextInfo = NEXT_STATUS[job.status];
  // Only show transition button to the correct party
  const canAdvance = nextInfo && (
    nextInfo.allowedRole === "both"
      ? (isOwner || isAllottedLabor)
      : nextInfo.allowedRole === "labor"
        ? isAllottedLabor
        : isOwner
  );

  const canCall = CALL_ENABLED_STATUSES.includes(job.status);

  return (
    <div className="pt-14 min-h-screen bg-[var(--color-bp-gray-100)]">
      <div className="max-w-3xl mx-auto px-6 py-12">
        {/* Toast */}
        {toast && (
          <div className="fixed top-20 left-1/2 -translate-x-1/2 z-50 animate-fade-in-up">
            <div className="px-6 py-3 rounded-2xl bg-[var(--color-bp-black)] text-white text-sm font-medium shadow-lg">
              {toast}
            </div>
          </div>
        )}

        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => router.back()}
            className="text-[var(--color-bp-blue)] text-sm font-medium mb-4 inline-flex items-center gap-1 hover:underline"
          >
            ← Back
          </button>
          <div className="flex items-start justify-between gap-4">
            <h1 className="text-3xl font-semibold tracking-tight text-[var(--color-bp-black)]">
              {job.title}
            </h1>
            <span
              className={`inline-flex items-center px-4 py-1.5 rounded-full text-sm font-medium border whitespace-nowrap ${
                STATUS_COLORS[job.status]
              }`}
            >
              {STATUS_LABELS[job.status]}
            </span>
          </div>
        </div>

        {/* Progress Bar — visible to employer and assigned labor for non-posted jobs */}
        {job.status !== "posted" && (isOwner || isAllottedLabor) && (
          <div className="card !p-5 mb-4">
            <h3 className="text-sm font-semibold text-[var(--color-bp-gray-500)] uppercase tracking-wider mb-3">
              Task Progress
            </h3>
            <ProgressBar status={job.status} />
          </div>
        )}

        {error && (
          <div className="p-4 rounded-xl bg-red-50 text-red-700 text-sm border border-red-200 mb-6">
            {error}
          </div>
        )}

        {/* Job Details */}
        <div className="card !p-6 mb-4">
          <h3 className="text-sm font-semibold text-[var(--color-bp-gray-500)] uppercase tracking-wider mb-4">
            Job Details
          </h3>
          <div className="grid grid-cols-2 gap-y-4 gap-x-8">
            <div>
              <div className="text-xs text-[var(--color-bp-gray-500)]">Work Type</div>
              <div className="font-medium">{wdLabel(job.work_description)}</div>
            </div>
            <div>
              <div className="text-xs text-[var(--color-bp-gray-500)]">Category</div>
              <div className="font-medium capitalize">{job.category}</div>
            </div>
            <div>
              <div className="text-xs text-[var(--color-bp-gray-500)]">Location</div>
              <div className="font-medium">
                {job.city} · {job.location_type === "online" ? "Online" : "Offline"}
              </div>
            </div>
            <div>
              <div className="text-xs text-[var(--color-bp-gray-500)]">Date</div>
              <div className="font-medium">
                {new Date(job.date_of_task).toLocaleDateString("en-IN", {
                  day: "numeric",
                  month: "long",
                  year: "numeric",
                })}
              </div>
            </div>
            <div>
              <div className="text-xs text-[var(--color-bp-gray-500)]">Time Span</div>
              <div className="font-medium capitalize">{job.time_span.replace("_", " ")}</div>
            </div>
            <div>
              <div className="text-xs text-[var(--color-bp-gray-500)]">Organization</div>
              <div className="font-medium capitalize">{job.organization_type}</div>
            </div>
            {job.required_skill && (
              <div className="col-span-2">
                <div className="text-xs text-[var(--color-bp-gray-500)]">Required Skill</div>
                <div className="font-medium">{job.required_skill}</div>
              </div>
            )}
            {job.address && (
              <div className="col-span-2">
                <div className="text-xs text-[var(--color-bp-gray-500)]">Address</div>
                <div className="font-medium">{job.address}</div>
              </div>
            )}
          </div>
          <div className="mt-4 pt-4 border-t border-[var(--color-bp-gray-200)]">
            <div className="text-xs text-[var(--color-bp-gray-500)] mb-1">Description</div>
            <p className="text-[var(--color-bp-gray-700)] leading-relaxed">
              {job.role_description}
            </p>
          </div>
        </div>

        {/* Assigned Labor (visible to employer) */}
        {isOwner && job.allotted_labor_id && job.allotted_labor_name && (
          <div className="card !p-6 mb-4">
            <h3 className="text-sm font-semibold text-[var(--color-bp-gray-500)] uppercase tracking-wider mb-3">
              Assigned Worker
            </h3>
            <div className="flex items-center justify-between">
              <div>
                <div className="font-semibold text-[var(--color-bp-black)] text-lg">
                  {job.allotted_labor_name}
                </div>
                {job.accepted_at && (
                  <div className="text-xs text-[var(--color-bp-gray-500)] mt-0.5">
                    Accepted {new Date(job.accepted_at).toLocaleString("en-IN")}
                  </div>
                )}
              </div>
              {canCall && (
                <CallButton
                  userId={job.allotted_labor_id}
                  userName={job.allotted_labor_name}
                  jobId={job.id}
                  variant="full"
                />
              )}
            </div>
          </div>
        )}

        {/* Financial — Platform Custody Model */}
        <div className="card !p-6 mb-4">
          <h3 className="text-sm font-semibold text-[var(--color-bp-gray-500)] uppercase tracking-wider mb-4">
            Payment
          </h3>
          <div className="flex items-center justify-between mb-3">
            <span className="text-[var(--color-bp-gray-500)]">Budget</span>
            <span className="text-2xl font-semibold">₹{job.budget.toFixed(0)}</span>
          </div>
          {/* Employer sees full breakdown */}
          {(isOwner || user?.is_admin) && (
            <div className="text-sm space-y-1.5 text-[var(--color-bp-gray-500)]">
              <div className="flex justify-between">
                <span>Platform Commission (3%)</span>
                <span>₹{job.platform_commission.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span>Worker Payout (97%)</span>
                <span>₹{job.worker_payout.toFixed(2)}</span>
              </div>
              <div className="flex justify-between font-semibold text-[var(--color-bp-black)] pt-1 border-t border-[var(--color-bp-gray-200)]">
                <span>You Pay</span>
                <span>₹{job.budget.toFixed(2)}</span>
              </div>
            </div>
          )}
          {/* Worker only sees their payout */}
          {isAllottedLabor && !user?.is_admin && (
            <div className="text-sm space-y-1.5 text-[var(--color-bp-gray-500)]">
              <div className="flex justify-between">
                <span>Platform Fee (3%)</span>
                <span>-₹{job.platform_commission.toFixed(2)}</span>
              </div>
              <div className="flex justify-between font-semibold text-[var(--color-bp-black)]">
                <span>You Receive</span>
                <span>₹{job.worker_payout.toFixed(2)}</span>
              </div>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="space-y-4">
          {/* ─── Accept Task (instant, first-come-first-serve) ─── */}
          {canAccept && (
            <div className="card !p-6">
              <h3 className="text-lg font-semibold text-[var(--color-bp-black)] mb-3">
                Apply for this Job
              </h3>
              <p className="text-sm text-[var(--color-bp-gray-500)] mb-4">
                Click below to instantly accept this task. First come, first served.
              </p>
              <button
                id="accept-task-btn"
                onClick={handleAcceptTask}
                disabled={actionLoading}
                className="btn-primary w-full !py-4 text-lg"
              >
                {actionLoading ? "Accepting..." : "Accept Task"}
              </button>
            </div>
          )}

          {/* Task already assigned indicator */}
          {!isOwner && !isAllottedLabor && job.status !== "posted" && job.allotted_labor_id && (
            <div className="card !p-8 text-center bg-gray-50 border-gray-200">
              <div className="text-4xl mb-3">✅</div>
              <h3 className="text-lg font-semibold text-[var(--color-bp-black)] mb-1">Already Assigned</h3>
              <p className="text-[var(--color-bp-gray-500)]">
                This task has been claimed by another worker.
              </p>
            </div>
          )}

          {/* Status Transitions (work stages — role-scoped) */}
          {canAdvance && nextInfo && (
            <button
              onClick={() => handleTransition(nextInfo.target)}
              disabled={actionLoading}
              className="btn-primary w-full !py-4"
            >
              {actionLoading
                ? "Updating..."
                : `Mark as: ${STATUS_LABELS[nextInfo.target as keyof typeof STATUS_LABELS]}`}
            </button>
          )}

          {/* ═══════════════════════════════════════════════════════ */}
          {/* PLATFORM CUSTODY PAYMENT FLOW                          */}
          {/* ═══════════════════════════════════════════════════════ */}

          {/* Step 1: Employer initiates payment — show method selector */}
          {isOwner && job.status === "work_completed" && (
            <div className="card !p-6">
              <h3 className="text-lg font-semibold text-[var(--color-bp-black)] mb-3">
                Initiate Payment
              </h3>
              <p className="text-sm text-[var(--color-bp-gray-500)] mb-4">
                Pay to the BridgePoint platform. We will release 97% to the worker after verification.
              </p>
              <div className="flex gap-3 mb-4">
                <button
                  onClick={() => setPaymentMethod("upi")}
                  className={`flex-1 py-3 rounded-xl text-sm font-medium border transition-all ${
                    paymentMethod === "upi"
                      ? "bg-[var(--color-bp-blue)] text-white border-[var(--color-bp-blue)]"
                      : "bg-white text-[var(--color-bp-gray-700)] border-[var(--color-bp-gray-300)]"
                  }`}
                >
                  UPI
                </button>
                <button
                  onClick={() => setPaymentMethod("cash")}
                  className={`flex-1 py-3 rounded-xl text-sm font-medium border transition-all ${
                    paymentMethod === "cash"
                      ? "bg-[var(--color-bp-blue)] text-white border-[var(--color-bp-blue)]"
                      : "bg-white text-[var(--color-bp-gray-700)] border-[var(--color-bp-gray-300)]"
                  }`}
                >
                  Cash
                </button>
              </div>
              <button
                onClick={handlePayment}
                disabled={actionLoading}
                className="btn-primary w-full !py-3"
              >
                {actionLoading ? "Processing..." : `Initiate Payment — ₹${job.budget.toFixed(2)}`}
              </button>
            </div>
          )}

          {/* Step 2: Show Platform UPI QR + "Mark Payment Sent" */}
          {isOwner && job.status === "payment_in_process" && (
            <div className="card !p-6 text-center">
              <h3 className="text-lg font-semibold text-[var(--color-bp-black)] mb-4">
                Pay to Platform
              </h3>

              {/* Platform QR Code */}
              <div className="bg-white border-2 border-dashed border-[var(--color-bp-gray-300)] rounded-2xl p-6 mb-4 inline-block mx-auto">
                <img
                  src="/platform-qr.png"
                  alt="Platform UPI QR"
                  className="w-48 h-48 mx-auto"
                />
              </div>

              <div className="text-sm text-[var(--color-bp-gray-600)] mb-1">
                UPI ID: <strong className="text-[var(--color-bp-black)]">nirmal.2007000-2@okhdfcbank</strong>
              </div>
              <div className="text-2xl font-bold text-[var(--color-bp-black)] mb-1">
                ₹{job.budget.toFixed(2)}
              </div>
              <div className="text-xs text-[var(--color-bp-gray-500)] mb-4">
                Platform Commission (3%): ₹{job.platform_commission.toFixed(2)} · Worker Payout: ₹{job.worker_payout.toFixed(2)}
              </div>

              {/* UTR Reference Input */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-[var(--color-bp-gray-700)] mb-1.5 text-left">
                  UPI Transaction Reference (UTR) <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  className="input-field"
                  placeholder="Enter 12-digit UTR number"
                  value={upiRef}
                  onChange={(e) => setUpiRef(e.target.value.replace(/[^0-9]/g, ''))}
                  maxLength={22}
                />
                {upiRef.length > 0 && upiRef.length < 12 && (
                  <p className="text-xs text-red-500 mt-1 text-left">
                    UTR must be at least 12 digits.
                  </p>
                )}
                <p className="text-xs text-[var(--color-bp-gray-500)] mt-1 text-left">
                  Find this in your UPI app → Transaction History → Transaction Details.
                </p>
              </div>

              <button
                onClick={handleMarkSent}
                disabled={actionLoading || upiRef.length < 12}
                className="btn-primary w-full !py-4"
              >
                {actionLoading ? "Marking..." : "✓ I Have Sent the Payment"}
              </button>
            </div>
          )}

          {/* Step 3: Verification Pending — Employer waiting */}
          {isOwner && job.status === "verification_pending" && (
            <div className="card !p-8 text-center bg-yellow-50 border-yellow-100">
              <div className="text-4xl mb-3">⏳</div>
              <h3 className="text-lg font-semibold text-yellow-700 mb-1">Payment Sent</h3>
              <p className="text-sm text-yellow-600">
                Awaiting platform verification. We will confirm receipt shortly.
              </p>
              {job.payment_sent_at && (
                <p className="text-xs text-yellow-500 mt-2">
                  Sent: {new Date(job.payment_sent_at).toLocaleString("en-IN")}
                </p>
              )}
            </div>
          )}

          {/* Verified status — waiting for payout (removed: verified no longer exists) */}

          {/* Laborer waiting states */}
          {isAllottedLabor && job.status === "work_completed" && (
            <div className="card !p-8 text-center bg-blue-50 border-blue-100">
              <div className="text-4xl mb-3">💰</div>
              <h3 className="text-lg font-semibold text-[var(--color-bp-blue)] mb-1">Work Completed!</h3>
              <p className="text-sm text-blue-600 font-medium">
                Waiting for employer to pay.
              </p>
            </div>
          )}

          {isAllottedLabor && ["payment_in_process", "verification_pending"].includes(job.status) && (
            <div className="card !p-8 text-center bg-yellow-50 border-yellow-100">
              <div className="text-4xl mb-3">⏳</div>
              <h3 className="text-lg font-semibold text-yellow-700 mb-1">Payment in Progress</h3>
              <p className="text-sm text-yellow-600">
                Employer has initiated payment. Platform is verifying.
              </p>
              <p className="text-xs text-yellow-500 mt-2">
                You will receive ₹{job.worker_payout.toFixed(2)} once verified.
              </p>
            </div>
          )}

          {/* Payment Completed — Final State */}
          {(isOwner || isAllottedLabor) && ["payout_released", "payment_completed"].includes(job.status) && (
            <div className="card !p-8 text-center bg-emerald-50 border-emerald-100">
              <div className="text-4xl mb-3">🎉</div>
              <h3 className="text-lg font-semibold text-emerald-700 mb-1">Payment Completed!</h3>
              <p className="text-sm text-emerald-600">
                {isAllottedLabor
                  ? `₹${job.worker_payout.toFixed(2)} has been released to you.`
                  : "Worker payout has been released. Job complete!"}
              </p>
              {job.payout_released_at && (
                <p className="text-xs text-emerald-500 mt-2">
                  Released: {new Date(job.payout_released_at).toLocaleString("en-IN")}
                </p>
              )}
            </div>
          )}

          {/* Admin Actions */}
          {user?.is_admin && job.status === "verification_pending" && (
            <div className="card !p-6 bg-purple-50 border-purple-100">
              <h3 className="text-lg font-semibold text-purple-800 mb-3">
                🔐 Admin: Verify & Release Payout
              </h3>
              <div className="text-sm text-purple-600 mb-4 space-y-1">
                <div>Budget: ₹{job.budget.toFixed(2)}</div>
                <div>Commission: ₹{job.platform_commission.toFixed(2)}</div>
                <div>Worker Payout: ₹{job.worker_payout.toFixed(2)}</div>
              </div>
              <button
                onClick={handleAdminVerify}
                disabled={actionLoading}
                className="btn-primary w-full !py-3 !bg-purple-600"
              >
                {actionLoading ? "Verifying..." : "Confirm Payment & Release Payout"}
              </button>
            </div>
          )}

          {user?.is_admin && job.status === "payout_released" && (
            <div className="card !p-6 bg-purple-50 border-purple-100">
              <h3 className="text-lg font-semibold text-purple-800 mb-3">
                🔐 Admin: Mark Job Completed
              </h3>
              <div className="text-sm text-purple-600 mb-4">
                Worker has received ₹{job.worker_payout.toFixed(2)}. Finalize this job.
              </div>
              <button
                onClick={handleAdminRelease}
                disabled={actionLoading}
                className="btn-primary w-full !py-3 !bg-emerald-600"
              >
                {actionLoading ? "Completing..." : "Mark Job as Completed"}
              </button>
            </div>
          )}

          {/* Chat Panel — visible after task acceptance to participants */}
          {job.allotted_labor_id && (isOwner || isAllottedLabor) && (
            <ChatPanel jobId={jobId} isParticipant={true} />
          )}

          {/* Add to Favorites */}
          {isOwner &&
            job.allotted_labor_id &&
            ["payout_released", "payment_completed"].includes(job.status) && (
              <button
                onClick={handleAddFavorite}
                className="btn-secondary w-full !py-3"
              >
                ❤️ Save Worker to Favorites
              </button>
            )}
        </div>
      </div>
    </div>
  );
}
